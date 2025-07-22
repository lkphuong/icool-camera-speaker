import { exec } from "child_process";

export const setVolumeWindows = (volume: number) => {
  const vol = Math.max(0, Math.min(100, volume));
  const command =
    `powershell -Command "(New-Object -ComObject WScript.Shell).SendKeys([char]175)"`.repeat(
      vol / 2
    );

  exec(command, (error, stdout, stderr) => {
    if (error) {
      console.error(`Lỗi khi set âm lượng: ${error.message}`);
    }
  });
};

export const setVolumeMac = (volume: number) => {
  console.log(`Setting macOS volume to ${volume}%`);
  const normalized = Math.max(0, Math.min(100, volume)); // macOS volume: 0–100
  const command = `osascript -e "set volume output volume ${normalized}"`;
  console.log(`Setting macOS volume to ${normalized} (0-100 scale)`);
  exec(command, (error, stdout, stderr) => {
    if (error) {
      console.error(`Lỗi khi set âm lượng: ${error.message}`);
    }
  });
};
