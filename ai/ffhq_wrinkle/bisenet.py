"""BiSeNet architecture used by zllrunning/face-parsing.PyTorch.

Adapted from upstream commit d2e684cf1588b46145635e8fe7bcc29544e5537e
under the MIT License. See ``official/face_parsing/LICENSE.txt``.
"""

from __future__ import annotations

import torch
from torch import nn
from torch.nn import functional as F


def _conv3x3(in_channels: int, out_channels: int, stride: int = 1) -> nn.Conv2d:
    return nn.Conv2d(
        in_channels, out_channels, kernel_size=3, stride=stride, padding=1, bias=False
    )


class BasicBlock(nn.Module):
    def __init__(self, in_channels: int, out_channels: int, stride: int = 1):
        super().__init__()
        self.conv1 = _conv3x3(in_channels, out_channels, stride)
        self.bn1 = nn.BatchNorm2d(out_channels)
        self.conv2 = _conv3x3(out_channels, out_channels)
        self.bn2 = nn.BatchNorm2d(out_channels)
        self.relu = nn.ReLU(inplace=True)
        self.downsample = None
        if in_channels != out_channels or stride != 1:
            self.downsample = nn.Sequential(
                nn.Conv2d(in_channels, out_channels, 1, stride=stride, bias=False),
                nn.BatchNorm2d(out_channels),
            )

    def forward(self, value: torch.Tensor) -> torch.Tensor:
        residual = self.bn2(self.conv2(F.relu(self.bn1(self.conv1(value)))))
        shortcut = value if self.downsample is None else self.downsample(value)
        return self.relu(shortcut + residual)


def _basic_layer(
    in_channels: int, out_channels: int, block_count: int, stride: int
) -> nn.Sequential:
    blocks = [BasicBlock(in_channels, out_channels, stride)]
    blocks.extend(BasicBlock(out_channels, out_channels) for _ in range(block_count - 1))
    return nn.Sequential(*blocks)


class Resnet18(nn.Module):
    def __init__(self):
        super().__init__()
        self.conv1 = nn.Conv2d(3, 64, 7, stride=2, padding=3, bias=False)
        self.bn1 = nn.BatchNorm2d(64)
        self.maxpool = nn.MaxPool2d(3, stride=2, padding=1)
        self.layer1 = _basic_layer(64, 64, 2, 1)
        self.layer2 = _basic_layer(64, 128, 2, 2)
        self.layer3 = _basic_layer(128, 256, 2, 2)
        self.layer4 = _basic_layer(256, 512, 2, 2)

    def forward(self, value: torch.Tensor):
        value = self.maxpool(F.relu(self.bn1(self.conv1(value))))
        value = self.layer1(value)
        feat8 = self.layer2(value)
        feat16 = self.layer3(feat8)
        feat32 = self.layer4(feat16)
        return feat8, feat16, feat32


class ConvBNReLU(nn.Module):
    def __init__(self, in_channels: int, out_channels: int, kernel: int = 3,
                 stride: int = 1, padding: int = 1):
        super().__init__()
        self.conv = nn.Conv2d(
            in_channels, out_channels, kernel, stride, padding, bias=False
        )
        self.bn = nn.BatchNorm2d(out_channels)

    def forward(self, value: torch.Tensor) -> torch.Tensor:
        return F.relu(self.bn(self.conv(value)))


class BiSeNetOutput(nn.Module):
    def __init__(self, in_channels: int, mid_channels: int, classes: int):
        super().__init__()
        self.conv = ConvBNReLU(in_channels, mid_channels)
        self.conv_out = nn.Conv2d(mid_channels, classes, 1, bias=False)

    def forward(self, value: torch.Tensor) -> torch.Tensor:
        return self.conv_out(self.conv(value))


class AttentionRefinementModule(nn.Module):
    def __init__(self, in_channels: int, out_channels: int):
        super().__init__()
        self.conv = ConvBNReLU(in_channels, out_channels)
        self.conv_atten = nn.Conv2d(out_channels, out_channels, 1, bias=False)
        self.bn_atten = nn.BatchNorm2d(out_channels)

    def forward(self, value: torch.Tensor) -> torch.Tensor:
        feature = self.conv(value)
        attention = F.avg_pool2d(feature, feature.shape[2:])
        attention = torch.sigmoid(self.bn_atten(self.conv_atten(attention)))
        return feature * attention


class ContextPath(nn.Module):
    def __init__(self):
        super().__init__()
        self.resnet = Resnet18()
        self.arm16 = AttentionRefinementModule(256, 128)
        self.arm32 = AttentionRefinementModule(512, 128)
        self.conv_head32 = ConvBNReLU(128, 128)
        self.conv_head16 = ConvBNReLU(128, 128)
        self.conv_avg = ConvBNReLU(512, 128, kernel=1, padding=0)

    def forward(self, value: torch.Tensor):
        feat8, feat16, feat32 = self.resnet(value)
        average = F.avg_pool2d(feat32, feat32.shape[2:])
        average = F.interpolate(self.conv_avg(average), feat32.shape[2:], mode="nearest")
        feat32 = self.arm32(feat32) + average
        feat32_up = self.conv_head32(
            F.interpolate(feat32, feat16.shape[2:], mode="nearest")
        )
        feat16 = self.arm16(feat16) + feat32_up
        feat16_up = self.conv_head16(
            F.interpolate(feat16, feat8.shape[2:], mode="nearest")
        )
        return feat8, feat16_up, feat32_up


class FeatureFusionModule(nn.Module):
    def __init__(self, in_channels: int, out_channels: int):
        super().__init__()
        self.convblk = ConvBNReLU(in_channels, out_channels, kernel=1, padding=0)
        self.conv1 = nn.Conv2d(out_channels, out_channels // 4, 1, bias=False)
        self.conv2 = nn.Conv2d(out_channels // 4, out_channels, 1, bias=False)

    def forward(self, spatial: torch.Tensor, context: torch.Tensor) -> torch.Tensor:
        feature = self.convblk(torch.cat((spatial, context), dim=1))
        attention = F.avg_pool2d(feature, feature.shape[2:])
        attention = self.conv2(F.relu(self.conv1(attention)))
        return feature * torch.sigmoid(attention) + feature


class BiSeNet(nn.Module):
    """19-class face parser compatible with ``79999_iter.pth``."""

    def __init__(self, n_classes: int = 19):
        super().__init__()
        self.cp = ContextPath()
        self.ffm = FeatureFusionModule(256, 256)
        self.conv_out = BiSeNetOutput(256, 256, n_classes)
        self.conv_out16 = BiSeNetOutput(128, 64, n_classes)
        self.conv_out32 = BiSeNetOutput(128, 64, n_classes)

    def forward(self, value: torch.Tensor):
        height, width = value.shape[2:]
        feat8, context8, context16 = self.cp(value)
        fused = self.ffm(feat8, context8)
        size = (height, width)
        return (
            F.interpolate(self.conv_out(fused), size, mode="bilinear", align_corners=True),
            F.interpolate(self.conv_out16(context8), size, mode="bilinear", align_corners=True),
            F.interpolate(self.conv_out32(context16), size, mode="bilinear", align_corners=True),
        )
