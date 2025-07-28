"""
Windows Service wrapper for Audio Server
"""
import asyncio
import sys
import os
import socket
import servicemanager
import win32event
import win32service
import win32serviceutil
import logging
from main import AudioServer

class AudioServerService(win32serviceutil.ServiceFramework):
    _svc_name_ = "AudioServerService"
    _svc_display_name_ = "Audio Server Service"
    _svc_description_ = "WebSocket Audio Server Service"

    def __init__(self, args):
        win32serviceutil.ServiceFramework.__init__(self, args)
        self.hWaitStop = win32event.CreateEvent(None, 0, 0, None)
        self.server = None
        socket.setdefaulttimeout(60)

    def SvcStop(self):
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        win32event.SetEvent(self.hWaitStop)

    def SvcDoRun(self):
        servicemanager.LogMsg(servicemanager.EVENTLOG_INFORMATION_TYPE,
                            servicemanager.PYS_SERVICE_STARTED,
                            (self._svc_name_, ''))
        self.main()

    def main(self):
        try:
            # Setup logging for service
            log_path = os.path.join(os.path.dirname(__file__), "logs", "service.log")
            os.makedirs(os.path.dirname(log_path), exist_ok=True)
            
            logging.basicConfig(
                filename=log_path,
                level=logging.INFO,
                format='%(asctime)s - %(levelname)s - %(message)s'
            )
            
            logging.info("Audio Server Service starting...")
            
            # Create and start server
            allowed_ips = ["127.0.0.1", "::1", "localhost", "118.69.196.115"]
            self.server = AudioServer(host='0.0.0.0', port=8765, allowed_ips=allowed_ips)
            
            # Run the server in an asyncio event loop
            asyncio.run(self.run_server())
            
        except Exception as e:
            logging.error(f"Service error: {e}")
            servicemanager.LogErrorMsg(f"Service error: {e}")

    async def run_server(self):
        try:
            # Start the server
            server_task = asyncio.create_task(self.server.start())
            
            # Wait for stop event
            while win32event.WaitForSingleObject(self.hWaitStop, 1000) != win32event.WAIT_OBJECT_0:
                await asyncio.sleep(0.1)
            
            # Stop the server
            server_task.cancel()
            try:
                await server_task
            except asyncio.CancelledError:
                pass
            
            if self.server:
                self.server.cleanup()
                
        except Exception as e:
            logging.error(f"Server error: {e}")

if __name__ == '__main__':
    if len(sys.argv) == 1:
        servicemanager.Initialize()
        servicemanager.PrepareToHostSingle(AudioServerService)
        servicemanager.StartServiceCtrlDispatcher()
    else:
        win32serviceutil.HandleCommandLine(AudioServerService)
