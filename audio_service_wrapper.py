import win32serviceutil
import win32service
import win32event
import servicemanager
import socket
import asyncio
import threading
import sys
import os

# Import your main audio server
from main import AudioServer

class AudioSocketService(win32serviceutil.ServiceFramework):
    """Windows Service wrapper for Audio Socket Server"""
    
    _svc_name_ = "AudioSocketService"
    _svc_display_name_ = "Audio Socket Service"
    _svc_description_ = "WebSocket Audio Server Service for playing audio from clients"
    _svc_deps_ = None  # sequence of service names on which this depends
    
    def __init__(self, args):
        win32serviceutil.ServiceFramework.__init__(self, args)
        self.hWaitStop = win32event.CreateEvent(None, 0, 0, None)
        socket.setdefaulttimeout(60)
        self.is_alive = True
        self.server_thread = None
        self.loop = None
        
    def SvcStop(self):
        """Called when the service is asked to stop"""
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        win32event.SetEvent(self.hWaitStop)
        self.is_alive = False
        
        # Stop the asyncio loop
        if self.loop and not self.loop.is_closed():
            self.loop.call_soon_threadsafe(self.loop.stop)
        
        servicemanager.LogMsg(
            servicemanager.EVENTLOG_INFORMATION_TYPE,
            servicemanager.PYS_SERVICE_STOPPED,
            (self._svc_name_, '')
        )
        
    def SvcDoRun(self):
        """Called when the service is started"""
        servicemanager.LogMsg(
            servicemanager.EVENTLOG_INFORMATION_TYPE,
            servicemanager.PYS_SERVICE_STARTED,
            (self._svc_name_, '')
        )
        
        # Start the server in a separate thread
        self.server_thread = threading.Thread(target=self.run_server)
        self.server_thread.daemon = True
        self.server_thread.start()
        
        # Wait for stop signal
        win32event.WaitForSingleObject(self.hWaitStop, win32event.INFINITE)
        
    def run_server(self):
        """Run the audio server"""
        try:
            # Configure allowed IPs - add your IPs here
            allowed_ips = ["127.0.0.1", "::1", "localhost", "118.69.196.115"]
            
            # Create and start the audio server
            server = AudioServer(host='0.0.0.0', allowed_ips=allowed_ips)
            
            # Create new event loop for this thread
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
            
            # Run the server
            self.loop.run_until_complete(server.start())
            
        except Exception as e:
            servicemanager.LogErrorMsg(f"Error in audio server: {str(e)}")
            
    def log_message(self, message):
        """Log message to Windows Event Log"""
        servicemanager.LogMsg(
            servicemanager.EVENTLOG_INFORMATION_TYPE,
            servicemanager.PYS_SERVICE_STARTED,
            (self._svc_name_, message)
        )

if __name__ == '__main__':
    if len(sys.argv) == 1:
        servicemanager.Initialize()
        servicemanager.PrepareToHostSingle(AudioSocketService)
        servicemanager.StartServiceCtrlDispatcher()
    else:
        win32serviceutil.HandleCommandLine(AudioSocketService)
