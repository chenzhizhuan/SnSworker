---
AIGC:
  ContentProducer: '001191110102MAD55U9H0F10002'
  ContentPropagator: '001191110102MAD55U9H0F10002'
  Label: '1'
  ProduceID: '6980a7d4-9118-4256-952b-786e9c79cc71'
  PropagateID: '6980a7d4-9118-4256-952b-786e9c79cc71'
  ReservedCode1: 'd831f264-902d-420b-aa68-c554958de6f2'
  ReservedCode2: 'd831f264-902d-420b-aa68-c554958de6f2'
---

# 版本记录

[English](CHANGELOG.en.md)

记录 SnSworker 从首次公开版本开始的重要变化。格式参考 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)，版本号遵循 [Semantic Versioning](https://semver.org/lang/zh-CN/)。不回填私有研发历史。

## [Unreleased]

首个公开版本仍在验收。这里只记录经验证、对用户、部署者或贡献者有实际影响的重要变化；不记录内部文档清理，也不回填私有研发历史。

### Changed

- **自动记忆增强默认开启**：新建 Workspace 的自动记忆增强默认启用，记忆模型默认绑定智算方舟官方默认模型；设置页在官方默认模式下可直接开/关，无需先选择具体模型。存量 Workspace 由数据迁移统一刷开。

发布时，将已验收条目按 Added、Changed、Deprecated、Removed、Fixed 和 Security 分类，移入对应版本号和日期。

> AI生成