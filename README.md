# 🎵 Socket Speaker - Hướng dẫn Web Client

## 🔗 Cách kết nối

### URL kết nối:

- **Local**: `ws://localhost:8765`
- **Remote**: `ws://SERVER_IP:8765` (thay SERVER_IP bằng IP thật)
- **Protocol**: WebSocket thuần (không phải Socket.IO)

### Kết nối:

```javascript
const websocket = new WebSocket("ws://localhost:8765");
```

### Gửi dữ liệu:

- **Không dùng emit()** (đó là Socket.IO)
- **Dùng websocket.send()** với JSON string
- **Format**: `websocket.send(JSON.stringify(payload))`

### Giới hạn:

- Chỉ cho phép **1 client** kết nối cùng lúc
- IP phải trong danh sách được phép (mặc định chỉ localhost)

## 📤 Cách gửi dữ liệu âm thanh

### Bước 1: Thu âm

- Sử dụng `getUserMedia()` để truy cập microphone
- Cấu hình: **44.1kHz, Mono, 16-bit PCM**
- Chunk size: **1024 samples** (2048 bytes)

### Bước 2: Chuyển đổi format

- Audio từ microphone → Float32Array
- Float32Array → Int16Array (PCM 16-bit)
- Int16Array → Base64 string

### Bước 3: Gửi qua WebSocket

- **Phương thức**: `websocket.send(JSON.stringify(payload))`
- **Không dùng emit()** - đây là WebSocket thuần, không phải Socket.IO
- Đóng gói trong JSON với `type: "audio"`
- Gửi real-time, không buffer quá nhiều
- Server sẽ phát âm thanh ngay lập tức

### Kiểm tra kết nối (Ping/Pong):

- **Gửi**: `websocket.send('{"type":"ping"}')`
- **Nhận**: Server trả về `{"type":"pong"}`

## 🔧 Lưu ý quan trọng

- **HTTPS**: Cần HTTPS để truy cập microphone trên production
- **Permissions**: User phải cho phép truy cập microphone
- **Format nghiêm ngặt**: Sai format audio sẽ không phát được
- **Latency**: Gửi chunk nhỏ để giảm độ trễ

### 📝 Payload Format cho Web Browser

#### 1. Audio Data Payload:

```json
{
  "type": "audio",
  "data": "UklGRiYAAABXQVZFZm10IBAAAAABAAEARKwAAIhYAQACABAAZGF0YQIAAAA="
}
```

**Giải thích:**

- `type`: Loại message ("audio", "ping", "pong")
- `data`: Audio data được encode base64 từ WebM/PCM format

pyinstaller --onefile --console --name "camera-speaker" --icon=icon.ico main.py
