# 技術文件 — Tacet HealthCare

---

## 【系統建設】從零建立一個 Windows 桌面應用程式

本章節說明如何用與本專案相同的技術組合，從零開始建立一個具備系統匣（System Tray）、相機偵測、以及獨立視窗的 Windows 桌面 App。

---

### 1. 技術選型

| 層級 | 套件 | 用途 |
|---|---|---|
| GUI 框架 | `PyQt6` | 視窗、元件、事件迴圈、系統匣 |
| 跨執行緒通訊 | `PyQt6.QtNetwork` | `QLocalServer` / `QLocalSocket`（單一實例） |
| 相機擷取 | `opencv-python`（`cv2`） | 讀取 webcam 畫面、影像翻轉、文字覆蓋 |
| AI 臉部 / 手部偵測 | `mediapipe`（Tasks API） | `FaceLandmarker`、`HandLandmarker` |
| 數值計算 | `numpy` | EAR 計算、座標距離 |
| 打包工具 | `PyInstaller` | 將 Python 專案打包為單一 `.exe` 資料夾 |

---

### 2. 環境建立步驟

```powershell
# 1. 建立虛擬環境（固定使用 venv，不使用 conda 或 global install）
python -m venv .venv

# 2. 啟動虛擬環境（每次開發前都要執行）
.venv\Scripts\activate

# 3. 安裝核心套件
.venv\Scripts\pip.exe install PyQt6 opencv-python mediapipe numpy pyinstaller

# 4. 鎖定版本至 requirements.txt
.venv\Scripts\pip.exe freeze > requirements.txt

# 5. 日後從 requirements.txt 還原環境
.venv\Scripts\pip.exe install -r requirements.txt
```

> **重要**：所有 `python` 與 `pip` 指令均需加上 `.venv\Scripts\` 前綴，確保操作的是 venv 而不是系統 Python。

---

### 3. 專案資料夾結構（建議）

新建一個同類型 Windows App 時，建議按照以下結構組織：

```
my-app/
│
├── main.py                 ← 程式入口點（QApplication、系統匣、主視窗）
├── requirements.txt        ← 套件版本鎖定
├── my_app.spec             ← PyInstaller 打包設定
│
├── src/                    ← 所有業務邏輯模組（Python package）
│   ├── __init__.py         ← 空檔，讓 src/ 成為 package，允許相對 import
│   ├── main_window.py      ← QMainWindow 主視窗
│   ├── tray_icon.py        ← 系統匣圖示建立邏輯
│   ├── alert_window.py     ← 通用警告視窗元件
│   ├── settings.py         ← 設定資料結構（dataclass）+ JSON 讀寫
│   ├── settings_dialog.py  ← 設定 UI 對話框（QDialog）
│   ├── camera_thread.py    ← 相機擷取 + AI 偵測（QThread）
│   └── camera_utils.py     ← 工具函式（掃描可用相機）
│
├── assets/                 ← 靜態資源（圖示、圖片）
│   ├── logo.png            ← 應用程式圖示（PNG，供程式內嵌顯示）
│   └── logo.ico            ← 應用程式圖示（ICO，供 exe 檔案圖示使用）
│
├── models/                 ← AI 模型檔（首次執行時自動下載，不進 git）
│   ├── face_landmarker.task
│   └── hand_landmarker.task
│
├── scripts/                ← 開發工具腳本
│   ├── run.ps1             ← 快速執行開發版
│   └── build.ps1           ← 打包 + 輸出至 release/
│
└── release/                ← 打包後成品（不進 git，直接分發給使用者）
    ├── TacetHealthCare.exe
    ├── _internal/          ← PyInstaller 依賴函式庫與資源
    ├── models/             ← AI 模型（複製至此）
    └── settings.json       ← 使用者設定（執行時自動產生）
```

---

### 4. 必寫的核心檔案說明

#### 4.1 `main.py` — 入口點

```python
from PyQt6.QtWidgets import QApplication, QSystemTrayIcon, QMenu
from PyQt6.QtNetwork import QLocalServer, QLocalSocket

app = QApplication(sys.argv)
app.setQuitOnLastWindowClosed(False)   # 關閉視窗不等於退出程式
```

**必做事項：**
- 呼叫 `ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(...)` 讓 Windows 工作列顯示自訂圖示而非 Python 圖示
- `setQuitOnLastWindowClosed(False)` 確保關閉視窗後程式繼續在背景運行
- 使用 `QLocalServer` / `QLocalSocket` 實作單一實例（防止重複開啟）

#### 4.2 `src/__init__.py` — Package 標記

空檔，但不可省略。有了它，`src/` 才能被視為 Python package，`main.py` 才能用 `from src.xxx import ...` 的語法，`src/` 內部各模組才能用 `from .xxx import ...` 相對 import。

#### 4.3 `src/tray_icon.py` — 路徑處理的關鍵

```python
_BASE_DIR = getattr(sys, "_MEIPASS", None) or \
            os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
```

這是 PyInstaller 打包後路徑解析的核心模式：
- **開發環境**：`sys._MEIPASS` 不存在，走 `__file__` 相對路徑
- **打包後**：`sys._MEIPASS` 指向 `_internal/` 資料夾，靜態資源（assets）就在這裡

> **注意區分**：靜態資源（只讀）用 `sys._MEIPASS`；使用者可寫檔案（settings.json、models/）用 `os.path.dirname(sys.executable)`，即 `.exe` 的相鄰目錄。

#### 4.4 `src/camera_thread.py` — 背景執行緒

繼承 `QThread`，在 `run()` 方法內進行相機擷取與 AI 推論。UI 與運算完全分離：
- 用 `pyqtSignal` 傳遞結果到 UI 執行緒（Qt 保證跨執行緒安全）
- 不可在子執行緒直接操作 UI 元件

```python
class CameraThread(QThread):
    frame_ready = pyqtSignal(QImage)
    status_changed = pyqtSignal(str)
    # ... 更多 signal
```

#### 4.5 `my_app.spec` — PyInstaller 打包設定

```python
exe = EXE(
    ...
    console=False,           # 不顯示終端機視窗
    icon="assets/logo.ico",  # exe 檔案的圖示
)
```

**打包時的注意事項：**
- `datas` 欄位列出需要一起打包的靜態資源，格式為 `("來源路徑", "目標資料夾名稱")`
- mediapipe 需要用 `collect_all("mediapipe")` 蒐集所有隱含依賴
- `console=False` 讓打包後的 exe 不顯示黑色終端機視窗

---

### 5. PyInstaller 打包流程

```powershell
# 正式打包（--clean 確保清除舊的 build cache）
.venv\Scripts\pyinstaller.exe --clean tacet.spec

# 打包後產出位置
dist\TacetHealthCare\
├── TacetHealthCare.exe    ← 主程式
└── _internal\             ← 所有依賴（不可移動或刪除）
```

**分發規則**：整個 `dist\TacetHealthCare\` 資料夾必須一起分發，使用者執行 `TacetHealthCare.exe` 即可，不需安裝 Python。

---

### 6. Windows 圖示顯示注意事項

exe 檔圖示不更新時，需清除 Windows 圖示快取：

```powershell
Stop-Process -Name explorer -Force
Remove-Item "$env:LOCALAPPDATA\IconCache.db" -ErrorAction SilentlyContinue
Remove-Item "$env:LOCALAPPDATA\Microsoft\Windows\Explorer\iconcache*" -ErrorAction SilentlyContinue
Start-Process explorer
```

ICO 格式建議包含以下尺寸：16×16、32×32、48×48、256×256（32bpp），以確保在各種情境（工作列、檔案總管、Alt+Tab）下都清晰顯示。

---

## 【本專案介紹】Tacet HealthCare 完整檔案結構說明

---

### 專案概述

**Tacet HealthCare** 是一套執行於 Windows 11 的桌面健康監測工具，透過 webcam 同時監測三項指標：

| 功能 | 觸發條件 | 解除方式 |
|---|---|---|
| 眨眼提醒 | 偵測到臉部但超過 N 秒未眨眼 | 偵測到眨眼動作 |
| 久坐提醒 | 持續坐在電腦前超過 N 分鐘 | 點擊警告視窗 / 起身離開 3 秒 |
| 喝水提醒 | 超過 N 分鐘未偵測到喝水動作 | 點擊警告視窗 / 做出喝水手勢 1 秒 / 離開超過 5 分鐘 |

程式以系統匣（System Tray）模式在背景運行，關閉主視窗不會結束程式。

---

### 根目錄檔案

#### `main.py`

程式的唯一入口點，負責：

1. **stdout/stderr 重導向**：打包後無終端機視窗，將輸出導向 `error.log` 以便除錯
2. **Windows AppUserModelID**：呼叫 `ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("TacetHealthCare")`，讓工作列按鈕顯示自訂圖示而非 Python 預設圖示
3. **單一實例控制**：
   - 啟動時嘗試連線 `QLocalSocket("TacetHealthCare_v1")`
   - 若連線成功（已有實例在運行）→ 發送 `"show"` 訊息，然後自身立即退出
   - 若連線失敗（第一個實例）→ 建立 `QLocalServer` 監聽，接收到 `"show"` 時呼叫 `window.show()` / `raise_()` / `activateWindow()`
4. **應用程式組裝**：建立 `QApplication`、`QSystemTrayIcon`、`MainWindow`，設定系統匣選單（Show Window / Quit），啟動事件迴圈

#### `requirements.txt`

虛擬環境的完整套件清單，由 `pip freeze` 產生。核心依賴：
- `PyQt6` + `PyQt6-Qt6` + `PyQt6_sip`：GUI 框架
- `mediapipe`：AI 臉部與手部偵測
- `opencv-python`：相機擷取與影像處理
- `numpy`：數值計算（EAR 演算法、座標距離）

#### `tacet.spec`

PyInstaller 打包設定檔，定義打包行為：

| 設定項目 | 值 | 說明 |
|---|---|---|
| `datas` | `mp_datas + [("assets", "assets")]` | 將 mediapipe 資源 + assets/ 一同打包進 `_internal/` |
| `binaries` | `mp_binaries` | mediapipe 的原生動態函式庫 |
| `hiddenimports` | `mp_hiddenimports + ["PyQt6.sip", "cv2"]` | 靜態分析找不到的隱含 import |
| `excludes` | `scipy, pandas, IPython, notebook` | 排除 mediapipe 拉入但執行時不需要的重型套件，縮減體積 |
| `console` | `False` | 執行後不顯示黑色終端機視窗 |
| `icon` | `"assets/logo.ico"` | exe 檔案本身的圖示 |
| `upx` | `False` | 停用 UPX 壓縮，避免防毒軟體誤報 |

#### `settings.json`

使用者設定的持久化儲存檔，由程式自動產生和更新，格式範例：

```json
{
  "blink_enabled": true,
  "blink_threshold": 5.0,
  "sit_enabled": true,
  "sit_threshold": 30,
  "water_enabled": true,
  "water_threshold": 30
}
```

**路徑邏輯**：開發環境存在專案根目錄，打包後存在 `TacetHealthCare.exe` 的相鄰目錄（即 `release/`），確保使用者有寫入權限。

#### `CLAUDE.md`

提供給 Claude Code AI 助手的專案指引，包含環境啟動方式、常用指令、技術架構摘要，讓 AI 在不讀完所有程式碼的情況下也能快速了解專案。

#### `.gitignore`

排除不需進版控的項目：
- `.venv/`：虛擬環境（容量大，可重建）
- `models/`：AI 模型（首次執行自動下載）
- `dist/`、`build/`、`release/`：打包產出物
- `*.log`、`__pycache__/`：執行期產生的暫存檔

---

### `src/` — 核心業務邏輯

所有應用程式模組集中於此，作為 Python package 組織，模組間使用相對 import。

#### `src/__init__.py`

空檔。讓 Python 把 `src/` 識別為 package，使以下 import 語法成立：
- `main.py` 中：`from src.main_window import MainWindow`
- `src/` 內部：`from .settings import AppSettings`

#### `src/main_window.py`

繼承 `QMainWindow`，是使用者主要互動的視窗。

**職責：**
- 建立頂部工具列（相機選擇下拉選單、Rescan 按鈕、Settings 按鈕）
- 管理視訊顯示區域（`QLabel` 展示每幀 `QPixmap`）
- 建立並持有三個 `AlertWindow` 實例（眨眼 / 久坐 / 喝水）
- 建立 `CameraThread` 並連接所有 Signal/Slot
- **關閉行為覆寫**：`closeEvent` 攔截關閉事件，改為 `hide()` + 顯示系統匣提示，讓程式繼續在背景運行

**Signal / Slot 連線對照：**

| Thread Signal | 接收 Slot | 效果 |
|---|---|---|
| `frame_ready` | `_update_frame` | 更新視訊畫面 |
| `blink_detected` | `_on_blink` | 關閉眨眼警告，更新狀態列 |
| `no_blink_alert` | `_alert.show_alert` | 顯示紅色眨眼警告 |
| `sit_break_alert` | `_break_alert.show_alert` | 顯示藍色久坐警告 |
| `sit_break_away` | `_break_alert.dismiss` | 使用者起身，關閉久坐警告 |
| `water_break_alert` | `_water_alert.show_alert` | 顯示青色喝水警告 |
| `water_dismissed` | `_water_alert.dismiss` | 確認喝水，關閉喝水警告 |
| `status_changed` | `_status_label.setText` | 更新底部狀態文字 |

#### `src/camera_thread.py`

繼承 `QThread`，在子執行緒中執行相機擷取與 AI 推論，避免阻塞 UI。

**常數定義（可調整的偵測參數）：**

| 常數 | 預設值 | 說明 |
|---|---|---|
| `EAR_THRESHOLD` | `0.25` | EAR 低於此值視為眼睛閉合 |
| `CONSEC_FRAMES` | `2` | 需連續幾幀閉眼才計為一次眨眼 |
| `SIT_RESET_AWAY` | `300`（5分鐘） | 離開螢幕超過此秒數，久坐計時器歸零 |
| `SIT_AWAY_DISMISS` | `3.0` | 臉部消失幾秒後關閉久坐警告（起身偵測） |
| `WATER_RESET_AWAY` | `300`（5分鐘） | 離開超過此秒數，喝水計時器歸零 |
| `DRINK_HOLD_SECONDS` | `1.0` | 手部維持在嘴邊幾秒才確認為喝水 |
| `HAND_MOUTH_RATIO` | `0.55` | 手掌到嘴的距離 / 臉部寬度，小於此值才觸發 |
| `HAND_MOUTH_VERT_RATIO` | `0.50` | 垂直對齊容許度（防止手只是路過臉旁） |

**核心演算法：**

1. **眨眼偵測（EAR — Eye Aspect Ratio）**
   - 取左右眼各 6 個 landmark 座標
   - `EAR = (垂直距離1 + 垂直距離2) / (2 × 水平距離)`
   - EAR < 0.25 且持續 ≥ 2 幀 → 計為一次眨眼

2. **喝水手勢偵測**
   - 取手部 4 個掌根關節（MCP 5,9,13,17）的平均座標作為「手掌中心」
   - 計算手掌中心到嘴唇中心的距離，除以臉部寬度做正規化
   - 同時檢查水平距離（貼近嘴）和垂直距離（在嘴的高度），兩者都滿足才算近嘴
   - 連續滿足 1 秒 → 確認為喝水動作

3. **狀態面板覆蓋（`_draw_stats_panel`）**
   - 在 OpenCV 影像左上角繪製半透明資訊面板
   - 只顯示目前啟用中的功能列，面板高度根據列數動態計算
   - 顏色根據剩餘時間漸變：綠 → 黃 → 橘 → 紅

**執行緒生命週期：**
- `run()` 包含雙層 while 迴圈：外層處理相機重連，內層逐幀處理
- `stop()` 設定 `_running = False`，呼叫 `wait()` 等待子執行緒結束，確保資源安全釋放

#### `src/alert_window.py`

無框（FramelessWindow）常駐最上層的警告視窗，可重複使用於三種警告。

**特性：**
- `Qt.WindowType.FramelessWindowHint`：無標題列、無邊框
- `Qt.WindowType.WindowStaysOnTopHint`：永遠在最上層
- `Qt.WidgetAttribute.WA_ShowWithoutActivating`：顯示時不搶奪鍵盤焦點
- **脈衝動畫**：`QTimer` 每 500ms 在主色和暗色之間切換，讓警告視窗閃爍
- **建構參數 `click_to_dismiss`**：`True` 時點擊視窗關閉，`False`（眨眼警告）則只能靠偵測到眨眼關閉
- `dismissed` Signal：關閉時通知 `CameraThread` 重置對應計時器

#### `src/camera_utils.py`

單一工具函式 `scan_cameras(max_index=8)`，依序嘗試 index 0~7 開啟 `cv2.VideoCapture`，回傳成功的 `(index, label)` 清單，供主視窗的相機選擇下拉選單使用。

#### `src/settings.py`

使用 `@dataclass` 定義設定結構，提供 JSON 序列化/反序列化：

- **`AppSettings`** 欄位：`blink_enabled`、`blink_threshold`、`sit_enabled`、`sit_threshold`、`water_enabled`、`water_threshold`
- **`sit_threshold_sec` / `water_threshold_sec`** 屬性：將分鐘轉為秒，供 `CameraThread` 直接使用
- **`save()`**：寫入 `settings.json`
- **`load()`**：讀取 `settings.json`，欄位缺失時以 dataclass 預設值補齊，確保向前相容

**路徑策略**：`settings.json` 存在使用者可寫入的目錄（打包後為 `.exe` 相鄰目錄），而非 `_internal/`（唯讀）。

#### `src/settings_dialog.py`

繼承 `QDialog` 的設定對話框，全程深色主題。

**三個設定群組：**
- **Blink Reminder**：啟用開關 + `QDoubleSpinBox`（3~60 秒）
- **Sit Break Reminder**：啟用開關 + `QSpinBox`（1~120 分鐘）
- **Water Reminder**：啟用開關 + `QSpinBox`（1~120 分鐘）

每個群組的數值輸入框在勾選啟用時才可編輯（`toggled.connect(setEnabled)`）。儲存時直接修改傳入的 `AppSettings` 物件（傳參照，CameraThread 即時感知）再呼叫 `save()`。

#### `src/tray_icon.py`

建立 `QIcon` 的工廠函式：
1. 優先載入 `assets/logo.png`（使用 `sys._MEIPASS` 解析打包後路徑）
2. 若 logo 不存在則以 `QPainter` 程式化繪製一個眼睛圖示作為備援

---

### `assets/` — 靜態資源

| 檔案 | 用途 |
|---|---|
| `logo.png` | 程式內嵌圖示（系統匣、主視窗標題列、工作列） |
| `logo.ico` | exe 檔案圖示（PyInstaller 打包時嵌入） |
| `logo.jpg` | 原始圖片備份 |
| `logo_V1.png` / `logo_V1.ico` | 第一版 logo 備份 |

**ICO 規格**：`logo.ico` 包含 9 個尺寸（16×16 到 256×256，全部 32bpp），確保在所有 Windows 顯示情境下都清晰。

---

### `models/` — AI 模型檔

首次執行時由 `CameraThread._ensure_model()` 自動從 Google 下載，**不進 git 版控**（見 `.gitignore`）：

| 檔案 | 大小 | 下載來源 |
|---|---|---|
| `face_landmarker.task` | ~3.7 MB | MediaPipe 官方 CDN |
| `hand_landmarker.task` | ~8.3 MB | MediaPipe 官方 CDN |

打包版本中，模型存放在 `.exe` 相鄰的 `models/` 目錄，使用 `os.path.dirname(sys.executable)` 定位（可寫路徑，不在 `_internal/` 內）。

---

### `scripts/` — 自動化腳本

#### `scripts/run.ps1`

```powershell
$root = Split-Path $PSScriptRoot -Parent
& "$root\.venv\Scripts\python.exe" "$root\main.py"
```

開發時快速啟動的捷徑，等同於 `.venv\Scripts\python.exe main.py`。

#### `scripts/build.ps1`

完整打包流程自動化，步驟：
1. 執行 `pyinstaller.exe --clean tacet.spec`
2. 終止任何正在運行的 `TacetHealthCare.exe` 程序
3. 清空並重建 `release/` 資料夾
4. 將 `dist\TacetHealthCare\` 的所有內容複製至 `release/`
5. 清除 `dist/` 和 `build/` 暫存資料夾

---

### `release/` — 打包成品（不進 git）

完整的可分發應用程式，結構如下：

```
release/
├── TacetHealthCare.exe     ← 使用者執行的主程式
├── _internal/              ← 所有 Python 依賴、PyQt6、OpenCV、MediaPipe
│   ├── assets/             ← logo.png（打包時複製）
│   └── ...                 ← 大量 .dll 和 .pyd 檔案
├── models/                 ← AI 模型（首次執行後產生）
│   ├── face_landmarker.task
│   └── hand_landmarker.task
├── settings.json           ← 使用者設定（首次儲存後產生）
└── error.log               ← 程式例外記錄（發生錯誤時產生）
```

> `_internal/` 和 `TacetHealthCare.exe` 必須放在同一目錄，不可單獨移動 exe 執行。

---

### `.vscode/` — 編輯器設定

`settings.json` 包含 VS Code 的工作區設定（interpreter 路徑等），已在 `.gitignore` 中排除版控，避免不同開發者的本機路徑衝突。

---

### `.claude/` — AI 協作記憶

Claude Code 的對話記憶與 `MEMORY.md` 索引，存放跨對話的專案上下文。此資料夾僅供 AI 工具使用，與應用程式邏輯無關。
