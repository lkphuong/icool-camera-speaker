# Hướng dẫn tạo và chạy Windows Service

## Các bước thực hiện:

### 1. Chuẩn bị môi trường

```cmd
# Mở Command Prompt với quyền Administrator
# Di chuyển đến thư mục dự án
cd "C:\path\to\your\socket-speaker folder"
```

### 2. Build service

```cmd
# Chạy script build
build_service.bat
```

### 3. Cài đặt service

```cmd
# Chạy với quyền Administrator
dist\AudioSocketService.exe install
```

### 4. Khởi động service

```cmd
# Cách 1: Dùng net command
net start AudioSocketService

# Cách 2: Dùng sc command
sc start AudioSocketService

# Cách 3: Qua Services Management Console
services.msc
```

### 5. Kiểm tra trạng thái service

```cmd
# Kiểm tra service đang chạy
sc query AudioSocketService

# Xem log của service
# Mở Event Viewer > Windows Logs > Application
```

### 6. Dừng service

```cmd
# Cách 1: Dùng net command
net stop AudioSocketService

# Cách 2: Dùng sc command
sc stop AudioSocketService
```

### 7. Gỡ bỏ service (nếu cần)

```cmd
# Dừng service trước
net stop AudioSocketService

# Gỡ bỏ service
dist\AudioSocketService.exe remove
```

## Cấu hình service:

### Thay đổi allowed IPs:

Chỉnh sửa file `audio_service_wrapper.py`, tìm dòng:

```python
allowed_ips = ["127.0.0.1", "::1", "localhost", "118.69.196.115"]
```

Thêm hoặc thay đổi IP theo nhu cầu.

### Thay đổi port:

Chỉnh sửa trong class `AudioServer` initialization.

## Troubleshooting:

### Lỗi thường gặp:

1. **Access Denied**: Chạy Command Prompt với quyền Administrator
2. **Service not found**: Đảm bảo đã install service trước
3. **Port already in use**: Kiểm tra port 8765 có bị sử dụng không

### Xem log:

- Mở Event Viewer (eventvwr.msc)
- Tìm trong Windows Logs > Application
- Tìm Source là "AudioSocketService"

### Debug:

```cmd
# Chạy service ở chế độ debug (không install)
dist\AudioSocketService.exe debug
```

## Tự động khởi động:

Service sẽ tự động khởi động cùng Windows. Để thay đổi:

```cmd
# Set thành Manual start
sc config AudioSocketService start= demand

# Set thành Automatic start
sc config AudioSocketService start= auto

# Set thành Disabled
sc config AudioSocketService start= disabled
```
