# GitHub Access Troubleshooting

> 适用场景：我们仓库成员/协作者无法 clone、pull、push 私有仓库。
> 当前仓库形态：`zts212653/Deterministic-Agent-Runtime-Engine`（私有个人仓，不是组织仓）。

## 1. 快速决策：用 PAT 还是 SSH？

1. 长期开发、多人协作：优先 `SSH key`（稳定、无需频繁换 token）。
2. 公司网络限制 SSH（22 端口）或只允许 HTTPS：用 `classic PAT (repo scope)`。
3. `fine-grained PAT` 在 collaborator 场景容易被策略限制，连不上时优先改用 classic PAT。

## 2. 先做 3 个前置检查

1. 确认你已接受仓库协作邀请，且权限至少是 `Write`。
2. 确认远端地址正确：
```bash
git remote -v
```
3. 确认当前认证状态（如果安装了 GitHub CLI）：
```bash
gh auth status
```

## 3. 方案 A：classic PAT（HTTPS）

### 3.1 创建 classic PAT

1. 打开 [GitHub Tokens (classic)](https://github.com/settings/tokens)。
2. 选择 `Generate new token (classic)`。
3. 建议设置短有效期（例如 30 天）。
4. Scope 至少勾选：
   - `repo`（访问私有仓库必需）
5. 生成后立刻复制（页面只显示一次）。

### 3.2 配置并验证

1. 远端使用 HTTPS（示例）：
```bash
git remote set-url origin https://github.com/zts212653/Deterministic-Agent-Runtime-Engine.git
```
2. 推荐用 `gh` 注入 token（避免手敲多次）：
```bash
printf '%s' "$GITHUB_PAT" | gh auth login --hostname github.com --git-protocol https --with-token
```
3. 验证：
```bash
git ls-remote origin
```

> 注意：不要把 token 写进脚本、命令行历史或仓库文件。

## 4. 方案 B：SSH key（推荐）

### 4.1 生成并加载密钥

```bash
# 1) 生成 ed25519 密钥（替换为你自己的邮箱）
ssh-keygen -t ed25519 -C "your_email@example.com"

# 2) 启动 ssh-agent 并加入私钥（macOS/Linux）
eval "$(ssh-agent -s)"
ssh-add ~/.ssh/id_ed25519
```

### 4.2 上传公钥到 GitHub

1. 复制公钥：
```bash
cat ~/.ssh/id_ed25519.pub
```
2. 打开 [SSH and GPG keys](https://github.com/settings/keys)，点击 `New SSH key` 粘贴保存。

### 4.3 切换仓库到 SSH 并验证

```bash
git remote set-url origin git@github.com:zts212653/Deterministic-Agent-Runtime-Engine.git
ssh -T git@github.com
git ls-remote origin
```

## 5. 常见报错对照

### 5.1 `remote: Repository not found.` / `403`
- 常见原因：
  - 没接受协作邀请
  - token 权限不足或过期
  - 用了错误账号凭据
- 处理：
  1. 重新确认仓库权限
  2. 重新生成 classic PAT（`repo`）
  3. 清理本地旧凭据后重登

### 5.2 `Support for password authentication was removed`
- 原因：还在用 GitHub 密码做 HTTPS 鉴权。
- 处理：改用 classic PAT 或 SSH key。

### 5.3 `Permission denied (publickey)`
- 原因：SSH key 未加到账号，或 agent 未加载私钥。
- 处理：
```bash
ssh-add -l
ssh-add ~/.ssh/id_ed25519
ssh -T git@github.com
```

### 5.4 `fine-grained PAT` 能登录但 push 失败
- 原因：token 对 collaborator 场景权限不足或被策略限制。
- 处理：改用 classic PAT（`repo`）或 SSH key。

## 6. 安全与轮换建议

1. PAT 只给最小权限，且设置有效期。
2. 离开项目或设备丢失时立刻 revoke token/SSH key。
3. 定期轮换密钥（例如每 90 天）。
4. 不要在截图、日志、录屏里暴露 token。

## 7. 给队友的最短执行版本

如果队友“连不上私有仓”，直接发这段：

```text
1) 先确认你已接受仓库协作邀请（Write 权限）。
2) 先用 SSH（推荐）：
   - ssh-keygen -t ed25519 -C "你的邮箱"
   - 把 ~/.ssh/id_ed25519.pub 加到 https://github.com/settings/keys
   - git remote set-url origin git@github.com:zts212653/Deterministic-Agent-Runtime-Engine.git
   - ssh -T git@github.com && git ls-remote origin
3) 如果公司网络禁 SSH，再用 classic PAT（repo scope）+ HTTPS。
```

## 8. 参考文档（官方）

- [Managing your personal access tokens](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens)
- [Managing your SSH keys](https://docs.github.com/en/authentication/connecting-to-github-with-ssh/managing-ssh-keys)
- [About remote repositories](https://docs.github.com/en/get-started/git-basics/about-remote-repositories)
