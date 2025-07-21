var Service = require("node-windows").Service;

var svc = new Service({
  name: "icool-camera-speaker",
  description: "iCool Camera Speaker Service",
  script: "D:\\vtcode\\icool-camera-speaker\\dist\\main.js",
  nodeOptions: ["--harmony", "--max-old-space-size=4096"],
});

svc.on("install", function () {
  svc.start();
});

svc.install();
