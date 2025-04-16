        let socket = null;
        let videoProcessing = false;
        let videoElement = null;
        let canvas = null;
        let ctx = null;
        let videoDuration = 0;
        let currentHistoryPage = 0;
        const HISTORY_PER_PAGE = 10;
        let voiceEnabled = true;
        const speechSynthesis = window.speechSynthesis;

        // 初始化WebSocket连接
        function connectWebSocket() {
            if (socket && socket.readyState === WebSocket.OPEN) {
                return Promise.resolve();
            }

            updateStatus('connecting', '连接中...');

            return new Promise((resolve, reject) => {
                wsProtocol = window.location.protocol === "https:" ? "wss:" : "ws:";
                socket = new WebSocket(`${wsProtocol}//${window.location.host}/ws/detect`);

                socket.onopen = () => {
                    updateStatus('connected', '已连接');
                    resolve();
                };

                socket.onerror = (error) => {
                    updateStatus('disconnected', '连接错误');
                    reject(error);
                };

                socket.onclose = () => {
                    updateStatus('disconnected', '连接已关闭');
                };

                socket.onmessage = (event) => {
                    const data = JSON.parse(event.data);
                    if (data.type === 'detection_result') {
                        handleDetectionResult(data);
                    } else if (data.type === 'knowledge_answer') {
                        addMessage(data.question, true);
                        addMessage(data.answer, false);
                    } else if (data.type === 'video_status') {
                        if (data.status === 'processing') {
                            document.getElementById('performanceInfo').textContent = "视频处理中...";
                        } else if (data.status === 'completed') {
                            document.getElementById('performanceInfo').textContent = "视频处理完成";
                            stopVideoProcessing();
                        }
                    } else if (data.type === 'error') {
                        alert('错误: ' + data.message);
                    }
                };
            });
        }

        // 切换标签页
        function openTab(tabName) {
            const tabs = document.getElementsByClassName('tab-content');
            for (let i = 0; i < tabs.length; i++) {
                tabs[i].classList.remove('active');
            }

            const tabButtons = document.getElementsByClassName('tab');
            for (let i = 0; i < tabButtons.length; i++) {
                tabButtons[i].classList.remove('active');
            }

            document.getElementById(tabName).classList.add('active');
            event.currentTarget.classList.add('active');
        }

        // 更新连接状态显示
        function updateStatus(status, message) {
            const statusElement = document.getElementById('status');
            statusElement.className = status;
            statusElement.textContent = `状态: ${message}`;
        }

        // 预览上传的图片
        document.getElementById('imageInput').addEventListener('change', function(e) {
            const file = e.target.files[0];
            if (file) {
                document.getElementById('imageFileName').textContent = file.name;
                const reader = new FileReader();
                reader.onload = function(event) {
                    const preview = document.getElementById('imagePreview');
                    preview.src = event.target.result;
                    preview.style.display = 'block';
                }
                reader.readAsDataURL(file);
            }
        });

        // 预览上传的视频
        document.getElementById('videoInput').addEventListener('change', function(e) {
            const file = e.target.files[0];
            if (file) {
                document.getElementById('videoFileName').textContent = file.name;
                videoElement = document.getElementById('videoPreview');
                const videoURL = URL.createObjectURL(file);
                videoElement.src = videoURL;
                videoElement.style.display = 'block';

                videoElement.onloadedmetadata = function() {
                    videoDuration = videoElement.duration;
                };
            }
        });

        // 开始检测图片
        async function startDetection() {
            const fileInput = document.getElementById('imageInput');
            const file = fileInput.files[0];

            if (!file) {
                alert('请先选择图片');
                return;
            }

            try {
                await connectWebSocket();

                document.getElementById('resultImage').style.display = 'none';
                document.getElementById('detectionResults').style.display = 'none';
                document.getElementById('performanceInfo').textContent = "处理中...";

                const reader = new FileReader();
                reader.onload = async function(event) {
                    socket.send(event.target.result);
                };
                reader.readAsDataURL(file);

            } catch (error) {
                console.error('WebSocket错误:', error);
                alert('连接失败: ' + error.message);
            }
        }

        // 处理视频
        async function processVideo() {
            const fileInput = document.getElementById('videoInput');
            const file = fileInput.files[0];

            if (!file) {
                alert('请先选择视频');
                return;
            }

            try {
                await connectWebSocket();

                videoProcessing = true;
                document.getElementById('stopBtn').style.display = 'inline-block';
                document.getElementById('videoProgress').style.display = 'block';
                document.getElementById('performanceInfo').textContent = "准备处理视频...";

                // 通知服务器开始处理视频
                socket.send("video_start:" + file.name);

                // 创建视频元素处理视频帧
                const video = document.createElement('video');
                const videoURL = URL.createObjectURL(file);
                video.src = videoURL;

                canvas = document.getElementById('videoCanvas');
                ctx = canvas.getContext('2d');

                video.onloadedmetadata = function() {
                    canvas.width = video.videoWidth;
                    canvas.height = video.videoHeight;
                    canvas.style.display = 'block';
                    processVideoFrame(video);
                };

            } catch (error) {
                console.error('视频处理错误:', error);
                alert('处理失败: ' + error.message);
            }
        }
      //处理视频帧
        async function processVideoFrame(video) {
    if (!videoProcessing) return;

    const progress = (video.currentTime / video.duration) * 100;
    document.getElementById('videoProgress').value = progress;

    if (video.currentTime >= video.duration) {
        socket.send("video_end");
        return;
    }

    try {
        // 捕获当前帧
        ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
        const imageData = canvas.toDataURL('image/jpeg');

        // 发送帧到服务器处理
        socket.send(imageData);

        // 等待一段时间再处理下一帧
        await new Promise(resolve => setTimeout(resolve, 300)); // 300ms间隔

        // 继续处理下一帧
        video.currentTime += 0.5; // 每0.5秒处理一帧

        video.onseeked = function() {
            if (videoProcessing) {
                processVideoFrame(video);
            }
        };
    } catch (error) {
        console.error('处理视频帧出错:', error);
        stopVideoProcessing();
    }
}

// 停止视频处理
function stopVideoProcessing() {
    if (!videoProcessing) return;

    videoProcessing = false;
    document.getElementById('stopBtn').style.display = 'none';
    document.getElementById('performanceInfo').textContent = "视频处理已停止";

    // 发送停止命令到服务器
    if (socket && socket.readyState === WebSocket.OPEN) {
        socket.send("stop_processing");
    }
}

        // 处理检测结果
        function handleDetectionResult(data) {
            // 如果是视频处理，更新画布
            if (videoProcessing) {
                const img = new Image();
                img.onload = function () {
                    ctx.clearRect(0, 0, canvas.width, canvas.height);
                    ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
                };
                img.src = data.image;
            } else {
                // 图片处理逻辑保持不变
                const resultImage = document.getElementById('resultImage');
                resultImage.src = data.image;
                resultImage.style.display = 'block';
            }

            // 显示性能信息
            document.getElementById('performanceInfo').textContent =
                `处理时间: ${(data.process_time * 1000).toFixed(1)}ms`;

            // 显示检测结果
            const detectionResults = document.getElementById('detectionResults');
            const detectionList = document.getElementById('detectionList');
            const signDetails = document.getElementById('signDetails');

            detectionList.innerHTML = '';
            signDetails.innerHTML = '';

            if (data.detections && data.detections.length > 0) {
                data.detections.forEach(det => {
                    const item = document.createElement('div');
                    item.className = 'detection-item';
                    item.innerHTML = `
                        <strong>代号:</strong> ${det.class_code} <br>
                        <strong>类别:</strong> ${det.class} <br>
                        <strong>置信度:</strong> ${det.confidence.toFixed(2)}
                    `;
                    detectionList.appendChild(item);
                });

                if (data.sign_details && data.sign_details.length > 0) {

                    // 构建语音提示文本
                    const signNames = data.detections.map(det => det.class);
                    const uniqueNames = [...new Set(signNames)]; // 去重
                    const voiceText = `检测到${uniqueNames.join('和')}`;

                    data.sign_details.forEach(detail => {
                        const detailDiv = document.createElement('div');
                        detailDiv.className = 'sign-detail';
                        detailDiv.innerHTML = `
                            <h4>${detail.sign} 详细信息</h4>
                            <p>${detail.description.replace(/\n/g, '<br>')}</p>
                            <div class="sign-action">
                                <strong>建议行动:</strong>
                                <p>${detail.actions.replace(/\n/g, '<br>')}</p>
                            </div>
                        `;
                        signDetails.appendChild(detailDiv);
                    });

                    // 语音播报（延迟500ms避免干扰）
                    setTimeout(() => speak(voiceText), 500);
                }

                detectionResults.style.display = 'block';
            } else {
                detectionResults.style.display = 'block';
                detectionList.innerHTML = '<p>未检测到标志</p>';
            }
            fetchStats();

            if (data.detections && data.detections.length > 0) {
                setTimeout(loadHistory, 500);  // 延迟500ms确保后端已保存记录
            }
        }
            // 添加聊天消息
            function addMessage(text, isUser) {
                const chatBox = document.getElementById('chatBox');
                const messageDiv = document.createElement('div');
                messageDiv.className = `message ${isUser ? 'user-message' : 'bot-message'}`;
                messageDiv.textContent = text;
                chatBox.appendChild(messageDiv);
                chatBox.scrollTop = chatBox.scrollHeight;
            }

            // 提问
            function askQuestion() {
                const input = document.getElementById('questionInput');
                const question = input.value.trim();

                if (!question) {
                    alert('请输入问题');
                    return;
                }

                if (!socket || socket.readyState !== WebSocket.OPEN) {
                    alert('请先连接服务器');
                    return;
                }

                socket.send(`question:${question}`);
                fetchStats();
                input.value = '';
            }

            // 获取统计数据函数
            async function fetchStats() {
                try {
                    const response = await fetch('/api/stats');
                    if (response.ok) {
                        const data = await response.json();
                        document.getElementById('totalDetections').textContent = data.total_detections;
                        document.getElementById('dailyDetections').textContent = data.daily_detections;
                        document.getElementById('totalQuestions').textContent = data.total_questions;
                        document.getElementById('lastUpdate').textContent = data.last_update.split(' ')[1]; // 只显示时间
                    }
                } catch (error) {
                    console.error('获取统计数据失败:', error);
                }
            }

            function searchHistory() {
                  const searchText = document.getElementById('historySearch').value.trim();
                  if (searchText) {
                        loadHistory(true, searchText);
                  } else {
                        loadHistory(true);
                  }
            }

            async function loadHistory(reset = false, search = '') {
    if (reset) {
        currentHistoryPage = 0;
    }

    try {
        const response = await fetch(`/api/history?limit=${HISTORY_PER_PAGE}&offset=${currentHistoryPage * HISTORY_PER_PAGE}&search=${encodeURIComponent(search)}`);

        if (response.ok) {
            const data = await response.json();
            const historyList = document.getElementById('historyList');

            if (reset || data.has_search) {
                historyList.innerHTML = '';
                if (data.records.length === 0) {
                    historyList.innerHTML = '<div class="no-history">未找到匹配记录</div>';
                    return;
                }
            }

            renderHistory(data.records, data.search_term || '');

            if (!data.has_search && data.records.length === HISTORY_PER_PAGE) {
                addLoadMoreButton();
            }
        }
    } catch (error) {
        console.error('加载历史记录失败:', error);
    }
}

            function renderHistory(records, searchText = '') {
    const historyList = document.getElementById('historyList');

    records.forEach(record => {
        const item = document.createElement('div');
        item.className = 'history-item';

        // 检查是否是搜索结果并高亮
        const isMatch = searchText && record.detections.some(det =>
            det.class.toLowerCase().includes(searchText.toLowerCase()) ||
            det.class_code.toLowerCase().includes(searchText.toLowerCase())
        );

        if (isMatch) {
            item.classList.add('highlight');  // 添加高亮类
        }

        let imageHtml = '<div style="width:120px; height:90px; background:#eee; display:flex; align-items:center; justify-content:center; color:#999;">无图片</div>';
        if (record.image_data) {
            // 如果是匹配项，给图片添加高亮边框
            const highlightStyle = isMatch ? 'border: 2px solid #ffc107;' : '';
            imageHtml = `<img src="${record.image_data}" class="history-item-image" onclick="openModal('${record.image_data}')" style="${highlightStyle}">`;
        }

        let detectionsHtml = '<div>未检测到标志</div>';
        if (record.detections && record.detections.length > 0) {
            detectionsHtml = '<div class="history-item-detections">';
            record.detections.forEach(det => {
                // 高亮匹配文本
                let classText = det.class;
                let codeText = det.class_code;

                if (searchText) {
                    const regex = new RegExp(searchText, 'gi');
                    classText = classText.replace(regex, match => `<span class="highlight-text">${match}</span>`);
                    codeText = codeText.replace(regex, match => `<span class="highlight-text">${match}</span>`);
                }

                detectionsHtml += `<span class="history-detection-badge" title="置信度: ${det.confidence?.toFixed(2) || 'N/A'}">
                    ${codeText}: ${classText}
                </span>`;
            });
            detectionsHtml += '</div>';
        }

        item.innerHTML = `
            ${imageHtml}
            <div class="history-item-content">
                <div class="history-item-time">${record.timestamp}</div>
                ${detectionsHtml}
            </div>
        `;

        historyList.appendChild(item);
    });
}

            // 模态框功能
            function openModal(imageSrc) {
                const modal = document.getElementById('imageModal');
                const modalImg = document.getElementById('modalImage');
                modalImg.src = imageSrc;
                modal.style.display = 'block';
            }

            function closeModal() {
                document.getElementById('imageModal').style.display = 'none';
            }

            function addLoadMoreButton() {
                const loadMoreBtn = document.createElement('button');
                loadMoreBtn.className = 'btn';
                loadMoreBtn.textContent = '加载更多';
                loadMoreBtn.style.margin = '10px auto';
                loadMoreBtn.style.display = 'block';
                loadMoreBtn.onclick = () => loadHistory();
                document.getElementById('historyList').appendChild(loadMoreBtn);
            }

            function speak(text) {
                if (!voiceEnabled) return;

                    // 停止当前正在播报的内容
                    speechSynthesis.cancel();

                    // 创建新的语音实例
                    const utterance = new SpeechSynthesisUtterance();
                    utterance.text = text;
                    utterance.lang = 'zh-CN'; // 设置为中文
                    utterance.rate = 0.9; // 语速
                    utterance.pitch = 1; // 音调

                    // 语音播报
                    speechSynthesis.speak(utterance);

                    // 错误处理
                    utterance.onerror = (event) => {
                    console.error('语音播报错误:', event);
                    };
            }

            // 点击模态框外部关闭
            window.onclick = function (event) {
                const modal = document.getElementById('imageModal');
                if (event.target === modal) {
                    closeModal();
                }
            }

            // 页面加载时尝试连接
            window.addEventListener('load', () => {
                connectWebSocket().catch(() => {
                });
                fetchStats();
                // 设置定时刷新统计数据（每30秒）
                setInterval(fetchStats, 30000);
                loadHistory();

                if (!('speechSynthesis' in window)) {
                    console.warn('该浏览器不支持语音合成API');
                    document.getElementById('voiceControl').style.display = 'none';
                } else {
                    // 测试语音功能是否可用
                    try {
                        const testUtterance = new SpeechSynthesisUtterance(' ');
                        speechSynthesis.speak(testUtterance);
                        speechSynthesis.cancel();
                    } catch (e) {
                        console.warn('语音功能不可用:', e);
                        document.getElementById('voiceControl').style.display = 'none';
                    }
                }

                // 允许按Enter键提问
                document.getElementById('questionInput').addEventListener('keypress', (e) => {
                    if (e.key === 'Enter') {
                        askQuestion();
                    }
                });
                // 监听搜索框
                document.getElementById('historySearch').addEventListener('keypress', (e) => {
                    if (e.key === 'Enter') {
                       searchHistory();
                    }
                });
                // 语音开关功能
                document.getElementById('toggleVoiceBtn').addEventListener('click', function() {
                    voiceEnabled = !voiceEnabled;
                    const icon = document.getElementById('voiceIcon');
                    const status = document.getElementById('voiceStatus');

                    if (voiceEnabled) {
                        icon.textContent = '🔊';
                        status.textContent = '语音开启';
                        this.style.backgroundColor = '#4CAF50';
                        speak('语音提示已开启');
                    } else {
                        icon.textContent = '🔇';
                        status.textContent = '语音关闭';
                        this.style.backgroundColor = '#f44336';
                        speechSynthesis.cancel(); // 关闭时停止当前播报
                    }
                });
            });