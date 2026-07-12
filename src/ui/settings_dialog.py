from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QTabWidget, QWidget,
                              QFormLayout, QLineEdit, QComboBox, QPushButton,
                              QHBoxLayout, QGroupBox, QLabel, QSlider, QSpinBox,
                              QDialogButtonBox)
from PyQt6.QtCore import Qt
from character_engine.character_store import CharacterStore
import httpx


class SettingsDialog(QDialog):
    def __init__(self, store: CharacterStore, available_voices: list[dict], parent=None):
        super().__init__(parent)
        self.setWindowTitle("偏好设置")
        self.setMinimumWidth(500)
        self.setMinimumHeight(400)
        
        self._store = store
        self._available_voices = available_voices
        
        layout = QVBoxLayout(self)
        
        tabs = QTabWidget()
        tabs.addTab(self._create_llm_tab(), "LLM 模型")
        tabs.addTab(self._create_tts_tab(), "语音合成")
        tabs.addTab(self._create_cache_tab(), "缓存")
        layout.addWidget(tabs)
        
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._save_and_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        
        self._load_settings()
    
    def _create_llm_tab(self) -> QWidget:
        """LLM configuration tab."""
        w = QWidget()
        layout = QVBoxLayout(w)
        
        # LLM Mode
        mode_group = QGroupBox("LLM 模式")
        mode_layout = QVBoxLayout(mode_group)
        
        self._ollama_radio = QPushButton("Ollama (本地)")
        self._ollama_radio.setCheckable(True)
        self._cloud_radio = QPushButton("云端 API")
        self._cloud_radio.setCheckable(True)
        
        btn_layout = QHBoxLayout()
        btn_layout.addWidget(self._ollama_radio)
        btn_layout.addWidget(self._cloud_radio)
        mode_layout.addLayout(btn_layout)
        
        # Test connection button
        self._test_btn = QPushButton("测试连接")
        self._test_btn.clicked.connect(self._test_connection)
        self._test_status = QLabel("")
        mode_layout.addWidget(self._test_btn)
        mode_layout.addWidget(self._test_status)
        
        layout.addWidget(mode_group)
        
        # Cloud API settings
        cloud_group = QGroupBox("云端 API 设置")
        cloud_form = QFormLayout(cloud_group)
        
        self._endpoint_edit = QLineEdit()
        self._endpoint_edit.setPlaceholderText("https://api.openai.com/v1/chat/completions")
        cloud_form.addRow("API 端点:", self._endpoint_edit)
        
        self._api_key_edit = QLineEdit()
        self._api_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self._api_key_edit.setPlaceholderText("sk-...")
        cloud_form.addRow("API 密钥:", self._api_key_edit)
        
        self._model_edit = QLineEdit()
        self._model_edit.setPlaceholderText("gpt-4o-mini")
        cloud_form.addRow("模型名称:", self._model_edit)
        
        layout.addWidget(cloud_group)
        layout.addStretch()
        
        return w
    
    def _create_tts_tab(self) -> QWidget:
        """TTS configuration tab."""
        w = QWidget()
        layout = QVBoxLayout(w)
        
        # Narrator voice
        voice_group = QGroupBox("默认语音")
        voice_layout = QVBoxLayout(voice_group)
        
        narrator_form = QFormLayout()
        self._narrator_combo = QComboBox()
        for voice in self._available_voices:
            desc = voice.get("description", voice.get("name", ""))
            self._narrator_combo.addItem(desc, voice.get("name", ""))
        narrator_form.addRow("旁白语音:", self._narrator_combo)
        voice_layout.addLayout(narrator_form)
        
        layout.addWidget(voice_group)
        
        # Default speed
        speed_group = QGroupBox("默认播放设置")
        speed_form = QFormLayout(speed_group)
        
        self._default_speed_slider = QSlider(Qt.Orientation.Horizontal)
        self._default_speed_slider.setRange(50, 200)
        self._default_speed_slider.setValue(100)
        self._default_speed_label = QLabel("1.0x")
        self._default_speed_slider.valueChanged.connect(
            lambda v: self._default_speed_label.setText(f"{v/100:.1f}x")
        )
        speed_row = QHBoxLayout()
        speed_row.addWidget(self._default_speed_slider)
        speed_row.addWidget(self._default_speed_label)
        speed_form.addRow("默认速度:", speed_row)
        
        layout.addWidget(speed_group)
        layout.addStretch()
        
        return w
    
    def _create_cache_tab(self) -> QWidget:
        """Cache management tab."""
        w = QWidget()
        layout = QVBoxLayout(w)
        
        limit_group = QGroupBox("缓存限制")
        limit_form = QFormLayout(limit_group)
        
        self._cache_limit_spin = QSpinBox()
        self._cache_limit_spin.setRange(50, 5000)
        self._cache_limit_spin.setValue(500)
        self._cache_limit_spin.setSuffix(" MB")
        limit_form.addRow("最大缓存大小:", self._cache_limit_spin)
        
        layout.addWidget(limit_group)
        
        cache_info = QGroupBox("缓存信息")
        cache_layout = QVBoxLayout(cache_info)
        self._cache_size_label = QLabel("正在计算...")
        cache_layout.addWidget(self._cache_size_label)
        layout.addWidget(cache_info)
        
        clear_btn = QPushButton("清空缓存")
        clear_btn.clicked.connect(self._clear_cache)
        layout.addWidget(clear_btn)
        
        layout.addStretch()
        return w
    
    def _load_settings(self):
        """Load current settings from DB."""
        settings = self._store.get_all_settings()
        
        # LLM mode
        llm_mode = settings.get("llm_mode", "ollama")
        self._ollama_radio.setChecked(llm_mode == "ollama")
        self._cloud_radio.setChecked(llm_mode == "cloud")
        
        self._endpoint_edit.setText(settings.get("llm_endpoint", ""))
        self._api_key_edit.setText(settings.get("llm_api_key", ""))
        self._model_edit.setText(settings.get("llm_model", "gpt-4o-mini"))
        
        # Narrator voice
        narrator_voice = settings.get("narrator_voice", "zh-CN-XiaoxiaoNeural")
        for i in range(self._narrator_combo.count()):
            if self._narrator_combo.itemData(i) == narrator_voice:
                self._narrator_combo.setCurrentIndex(i)
                break
        
        # Default speed
        default_speed = settings.get("default_speed", "1.0")
        try:
            speed = int(float(default_speed) * 100)
            self._default_speed_slider.setValue(speed)
        except ValueError:
            pass
        
        # Cache limit
        cache_limit = settings.get("cache_size_limit_mb", "500")
        try:
            self._cache_limit_spin.setValue(int(cache_limit))
        except ValueError:
            pass
    
    def _save_and_accept(self):
        """Save settings to DB and accept dialog."""
        # LLM mode
        self._store.set_setting(
            "llm_mode", "ollama" if self._ollama_radio.isChecked() else "cloud"
        )
        self._store.set_setting("llm_endpoint", self._endpoint_edit.text())
        self._store.set_setting("llm_api_key", self._api_key_edit.text())
        self._store.set_setting("llm_model", self._model_edit.text())
        
        # Narrator voice
        narrator_voice = self._narrator_combo.currentData()
        if narrator_voice:
            self._store.set_setting("narrator_voice", narrator_voice)
        
        # Default speed
        speed = self._default_speed_slider.value() / 100.0
        self._store.set_setting("default_speed", f"{speed:.1f}")
        
        # Cache limit
        self._store.set_setting("cache_size_limit_mb", str(self._cache_limit_spin.value()))
        
        self.accept()
    
    def _test_connection(self):
        """Test the LLM connection."""
        self._test_status.setText("正在测试...")
        self._test_status.setStyleSheet("color: gray;")
        
        if self._ollama_radio.isChecked():
            try:
                with httpx.Client(timeout=httpx.Timeout(5.0)) as client:
                    resp = client.get("http://localhost:11434/api/tags")
                    if resp.status_code == 200:
                        self._test_status.setText("Ollama 连接成功")
                        self._test_status.setStyleSheet("color: green;")
                    else:
                        self._test_status.setText(f"Ollama 返回错误：HTTP {resp.status_code}")
                        self._test_status.setStyleSheet("color: red;")
            except Exception as e:
                self._test_status.setText(f"Ollama 连接失败：{e}")
                self._test_status.setStyleSheet("color: red;")
        else:
            endpoint = self._endpoint_edit.text()
            api_key = self._api_key_edit.text()
            if not endpoint or not api_key:
                self._test_status.setText("请填写 API 端点和密钥")
                self._test_status.setStyleSheet("color: red;")
                return
            
            try:
                with httpx.Client(timeout=httpx.Timeout(10.0)) as client:
                    resp = client.get(
                        endpoint.replace("/chat/completions", "/models"),
                        headers={"Authorization": f"Bearer {api_key}"}
                    )
                    if resp.status_code == 200:
                        self._test_status.setText("云端 API 连接成功")
                        self._test_status.setStyleSheet("color: green;")
                    else:
                        body = resp.text[:200]
                        self._test_status.setText(f"API 错误：HTTP {resp.status_code}")
                        self._test_status.setStyleSheet("color: red;")
            except Exception as e:
                self._test_status.setText(f"API 连接失败：{e}")
                self._test_status.setStyleSheet("color: red;")
    
    def _clear_cache(self):
        """Clear the TTS cache."""
        import os
        from ui.main_window import get_cache_dir
        cache_dir = get_cache_dir()
        try:
            count = 0
            for entry in os.listdir(cache_dir):
                if entry.endswith(".mp3"):
                    os.remove(os.path.join(cache_dir, entry))
                    count += 1
            self._cache_size_label.setText(f"已清除 {count} 个缓存文件")
        except Exception as e:
            self._cache_size_label.setText(f"清除失败：{e}")
    
    def showEvent(self, event):
        """Update cache size info when dialog is shown."""
        super().showEvent(event)
        try:
            import os
            from ui.main_window import get_cache_dir
            cache_dir = get_cache_dir()
            total = 0
            count = 0
            for entry in os.listdir(cache_dir):
                if entry.endswith(".mp3"):
                    total += os.path.getsize(os.path.join(cache_dir, entry))
                    count += 1
            self._cache_size_label.setText(
                f"缓存文件数：{count}\n总大小：{total / (1024*1024):.1f} MB"
            )
        except Exception:
            self._cache_size_label.setText("无法读取缓存信息")
