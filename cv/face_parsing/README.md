# cv.face_parsing

BiSeNet 人脸解析模型定义（19 类：皮肤/眉/眼/唇/头发/背景等）。

**来源**：[zllrunning/face-parsing.PyTorch](https://github.com/zllrunning/face-parsing.PyTorch)（MIT License）
**vendor 化改动**：仅将 `model.py` 的 `from resnet import ...` 改为包内相对导入（`from .resnet import ...`），其余未动。
上游的 `modules/`（InPlaceABN CUDA 扩展）在本项目中**未使用**——`model.py` 用的是标准 `nn.BatchNorm2d`。

## 权重文件（不入库）

`models/face_parsing/79999_iter.pth`（50.8MB，CelebAMask-HQ 训练权重，仅限非商业研究/教育用途），
从上游 README 提供的 Google Drive / 百度网盘链接下载后放入 `models/face_parsing/`。

## 首次运行注意

`resnet.py` 的 `Resnet18.init_weight()` 会从 `download.pytorch.org` 自动下载 ResNet18 backbone
（约 45MB，缓存于 `~/.cache/torch/hub/checkpoints/`）。服务器/离线环境请提前预热一次，或手动预置缓存文件。
