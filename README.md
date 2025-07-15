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
