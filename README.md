# VCA 补货监控：零基础安装教程

这套代码监控你指定的美国官网商品 VCARD35600（Vintage Alhambra bracelet, 5 motifs）。在 GitHub 云端运行，电脑关机也能检查。默认每 15 分钟计划运行一次，发现可见的 **ADD TO BAG** 就向 iPhone 的 Bark 和你的邮箱同时发送提醒。

**交付的是完整代码，尚未替你部署或开启监控。** 需要你自己创建仓库、添加 Secrets、完成一次实测。不要把密码或 Bark Key 发到聊天里。

## 1. 先了解运行规则

| 页面情况 | 处理 | 退出码 |
|---|---|---|
| ADD TO BAG 可见 | Bark + Gmail 各发送一次 | 两路均成功为 0，否则 1 |
| 只有 ORDER BY PHONE 可见 | 判为没货，不通知 | 0 |
| 两个都可见 | 按你的规则判为有货 | 两路均成功为 0，否则 1 |
| 两个都不可见 | UNKNOWN，保存截图，不当作没货 | 1 |
| 页面加载、访问或浏览器出错 | ERROR，尽可能保存截图和诊断记录 | 1 |

- 每次正常检测均保存截图和结果。浏览器根本启动不了或已崩溃时无法截图，仍返回 1 并尽可能保存错误类型。
- 不是在 HTML 中搜索字符串。程序找 button/link 控件，逐个调用 Playwright 的 `is_visible()`，额外排除透明控件及透明祖先。隐藏的第一个按钮不会遮蔽后面可见的重复按钮。
- “可见”按页面布局和 CSS 显示判断，不要求按钮处在首屏；不检测所有遮挡层、裁剪或实际可点击性。按你的要求，按钮即使 disabled，只要可见仍判有货。
- 页面打开后先等 12 秒，再最多观察 35 秒，让动态库存加载；观察期间出现有货立即返回。这个等待不能保证网站所有异步请求都已完成。
- 每个计划周期都是独立检查，**没有去重、没有冷却时间：持续有货会持续提醒，夜里也一样。** 购买后按第 9 节暂停。
- 不下单、不付款、不登录 VCA。实际库存以你打开商品页和结账时为准。

## 2. 在 iPhone 安装 Bark 并开启重要警告

Bark 通过设备 Key 找到你的 iPhone，不使用手机号。`call=1` 是持续响铃参数，不是电话呼叫。

1. 在 iPhone 打开 **App Store**。
2. 点右下角 **搜索**，输入 `Bark`。也可以直接打开 [Bark 官方 App Store 页面](https://apps.apple.com/app/bark-custom-notifications/id1403753865)。
3. 找到 **Bark - Custom Notifications**，点 **获取**，按提示安装。
4. 点 **打开**。系统询问是否允许通知时，点 **允许**；询问重要警告/关键警报权限时也点 **允许**。
5. 回到 iPhone 主屏幕，打开 **设置 → 通知 → Bark**。部分系统也能从 **设置 → App → Bark → 通知** 进入。
6. 打开 **允许通知**、**声音**、**重要警告 / Critical Alerts**（中文名称因系统版本可能不同）。锁定屏幕通知也打开。
7. 如果没有重要警告开关，先更新 Bark，打开 Bark 内的重要警告示例/设置并按提示请求权限，再回到系统通知设置检查。仅开启“时效性通知”不等于允许重要警告。
8. 回到 Bark 主界面，找到它显示的推送地址，大致形如 `https://api.day.app/你的设备Key/测试内容`。
9. 只复制 `api.day.app/` 后面第一段 Key，不包含斜杠、测试内容或整个网址。第 5 节把它放到 `BARK_KEY`。
10. 本代码使用官方 `api.day.app` 服务。如果你的 Bark 使用自建服务器，请先切换到官方服务并复制该服务的 Key；不要把自建地址中的 Key 混用。

代码发送 `level=critical`、`call=1`、`volume=10`、`sound=alarm`。Bark 官方说明重要警告可绕过静音/勿扰，`call=1` 可连续响铃约 30 秒。但必须获得系统权限，而且手机要有网络、开机；推送服务接收成功也不等于手机一定收到。**第 6 节必须实际做一次“静音 + 睡眠专注模式 + 锁屏”测试。**

依据：[Bark 官方说明](https://github.com/Finb/Bark)、[Bark API 参数](https://github.com/Finb/bark-server/blob/master/docs/API_V2.md)。

## 3. 为 Gmail 创建 App Password

发件邮箱可以就是收件邮箱 `zhaoxinli73@gmail.com`，也可以是你自己另一个 Gmail。下面选择你实际用来发件的账号。

1. 在电脑浏览器打开 [Google 账号](https://myaccount.google.com/)，登录发件 Gmail。
2. 点右上角头像，核对当前邮箱。后面 `GMAIL_USER` 必须填写这个账号。
3. 点左侧 **安全性 / Security**（有的界面显示“安全性和登录”）。
4. 在 **您如何登录 Google / How you sign in to Google** 中，点 **两步验证 / 2-Step Verification**。
5. 如果未开启，点 **开始使用 / Get started** 或 **开启两步验证**，按 Google 提示完成验证。
6. 开启后打开 [应用专用密码页面](https://myaccount.google.com/apppasswords)。按提示重新登录。
7. 在应用名称中输入 `VCA Monitor`，点 **创建 / Create**。
8. 复制弹窗里的 16 位应用专用密码，暂时留着这个窗口；第 5 节把它粘贴到 `GMAIL_APP_PASSWORD`。代码会自动去掉分组空格。
9. 这不是你的普通 Gmail 登录密码，不要填写普通密码。

如果没有“应用专用密码”：确认登录的是正确账号且已开启两步验证。组织账号、仅安全密钥的两步验证或高级保护等设置可能不支持；参见 [Google 官方说明](https://support.google.com/accounts/answer/185833)。如果之后改了 Google 账号密码，原 App Password 可能被撤销，需要重新生成并更新 Secret。

## 4. 创建 GitHub 仓库并上传代码

推荐用电脑浏览器操作。无须安装 Python、终端或 Git。

### 4.1 解压下载包

1. 下载本次交付的 `vca-restock-monitor.zip`。
2. Mac：在“下载”文件夹双击压缩包。Windows：右键压缩包 → **全部解压缩** → **提取**。
3. 打开解压得到的 `vca-restock-monitor` 文件夹。你会看到 `monitor.py`、`requirements.txt`、`README.md`、`tests` 等。
4. `.github` 是隐藏目录，后面会在 GitHub 网页中手动创建里面的文件，避免上传时漏掉。

### 4.2 新建仓库

1. 打开 [GitHub](https://github.com/)，注册或登录自己的账号。
2. 点页面右上角 **+ → New repository**，或直接打开 [创建仓库](https://github.com/new)。
3. **Repository name** 填 `vca-restock-monitor`。
4. 选择 **Private**，让代码、日志和截图只对有权限的人可见。
5. 勾选 **Add a README file**（新版界面可能是 README 开关），其余保持默认。
6. 点 **Create repository**。

### 4.3 上传普通文件

1. 在新仓库 **Code** 页面点 **Add file → Upload files**。
2. 从电脑文件夹拖入 `monitor.py` 和 `requirements.txt`。再拖入 `tests` 文件夹；README 可以一起上传覆盖初始说明。
3. 不要上传整个外层目录，否则会多套一层路径；也不要上传 ZIP，GitHub 不会自动解压它。
4. 页面底部的提交说明填 `Add monitor code`。
5. 点绿色 **Commit changes**。
6. 回到 Code 页，确认根目录直接能看到 `monitor.py`、`requirements.txt` 和 `tests`，不是藏在另一层 `vca-restock-monitor/` 中。

### 4.4 创建自动运行配置（这一步不能漏）

1. 在电脑打开解压目录中的 `.github/workflows/monitor.yml`。
   - Mac：Finder 中按 **Command + Shift + .** 显示隐藏文件，进入 `.github → workflows`，右键 `monitor.yml` → **打开方式 → 文本编辑**。
   - Windows：文件资源管理器点 **查看 → 显示 → 隐藏的项目**，进入 `.github → workflows`，右键 `monitor.yml` → **打开方式 → 记事本**。
2. 在编辑器里按 **Command+A、Command+C**（Windows 为 **Ctrl+A、Ctrl+C**）复制全部内容。不要修改缩进。
3. 回到 GitHub 仓库 Code 页，点 **Add file → Create new file**。
4. 顶部 **Name your file** 填完整路径 `.github/workflows/monitor.yml`。GitHub 会自动建立目录。
5. 在下方大编辑框中粘贴刚复制的内容。不要加 Markdown 的三个反引号。
6. 点 **Commit changes…**，在弹窗中选择直接提交到 `main`，再点 **Commit changes**。
7. 按同样步骤创建 `.github/workflows/tests.yml`，内容复制自下载包中的同名文件。
8. 可选：用同样方式创建根目录 `.gitignore`，复制包中的内容。

**监控配置提交到默认分支后，定时任务就具备运行条件。请接着立即配置 Secrets。** 如果中途要离开，可先按第 9 节暂停，回来配置完成再启用。

最终目录应为：

```text
vca-restock-monitor/
├── monitor.py
├── requirements.txt
├── README.md
├── .gitignore
├── tests/
│   └── test_monitor.py
└── .github/
    └── workflows/
        ├── monitor.yml
        └── tests.yml
```

## 5. 添加四个 GitHub Secrets

1. 进入刚创建的仓库，点顶部 **Settings**。注意是仓库设置，不是右上角头像里的个人设置。
2. 在左侧找到 **Security** 区域，点 **Secrets and variables → Actions**。
3. 确保在 **Secrets** 标签，不是 Variables。
4. 点 **New repository secret**。
5. 按下面的表分别填 **Name** 和 **Secret**，每填一个就点 **Add secret**，再点 **New repository secret** 添加下一个。

| Name（逐字复制） | Secret 填什么 |
|---|---|
| `BARK_KEY` | 第 2 节复制的 Bark 设备 Key，仅 Key |
| `GMAIL_USER` | 发件 Gmail 完整地址；如果用你的邮箱发件，填 `zhaoxinli73@gmail.com` |
| `GMAIL_APP_PASSWORD` | 第 3 节生成的 16 位应用专用密码 |
| `EMAIL_TO` | `zhaoxinli73@gmail.com` |

保存后只看见名称、看不到明文内容，这是正常的。需要修改时点右侧铅笔图标 → 输入新值 → **Update secret**。名称大小写、下划线都必须一致。

工作流通过 `${{ secrets.名称 }}` 把值注入环境变量，Python 再读取环境变量。代码、仓库、日志都不需要写入密码或 Key；也不需要添加 GitHub Token。不要创建包含密码的 `.env` 文件上传。

官方参考：[在 GitHub Actions 中使用 Secrets](https://docs.github.com/en/actions/how-tos/write-workflows/choose-what-workflows-do/use-secrets)。

## 6. 先测试邮件，再测试 iPhone 响铃

### 6.1 测试邮件

1. 点仓库顶部 **Actions**。
2. 如果出现启用 Actions 的提示，点允许/启用按钮。如果进入的是推荐模板页面，先检查第 4.4 节文件路径和默认分支。
3. 左侧点 **VCA Restock Monitor**。
4. 右侧点 **Run workflow**。
5. Branch 选择 `main`，mode 下拉选择 **test-email**。
6. 点下拉框里的绿色 **Run workflow**。
7. 等几秒刷新页面，点刚出现的最新运行记录，再点 **monitor**。
8. 展开 **Run monitor or test**。看到 `email: accepted by server` 表示 Gmail 接受了邮件；再到收件箱确认收到标题含“测试邮件”的邮件。
9. 没看到时检查垃圾邮件、所有邮件。发件和收件同账号时也检查“已发送”。

这个模式等价于 `python monitor.py --test-email`，不会访问商品页，也不会让手机响铃。

### 6.2 测试关键警报

1. 把 iPhone 放在身边，保持联网。
2. 开启 iPhone 静音，然后打开 **控制中心 → 专注模式 → 睡眠**，再锁屏。
3. 回到 GitHub **Actions → VCA Restock Monitor → Run workflow**。
4. mode 选 **test-bark**，点绿色 **Run workflow**。
5. 观察 iPhone 是否收到“响铃测试”，并在静音和睡眠专注模式下播放声音。
6. 如果 GitHub 显示成功但不响，检查第 2 节的 **重要警告/Critical Alerts**、声音权限、设备网络以及 Key 是否属于这台手机。
7. 最后运行一次 **test-all**，确认邮件与 Bark 两个通道都能收到。

这是关键的实机验收步骤。不要仅凭 GitHub 的绿色勾就认为手机一定会响。

## 7. 测试按钮识别，再运行真实检测

### 7.1 跑自动测试（不访问 VCA，也不发通知）

1. 点 **Actions → Offline browser tests → Run workflow**。
2. 选择 `main`，点绿色 **Run workflow**。
3. 打开最新记录 → **tests**，查看最后一步。
4. 期望结果为全部测试通过。这会用真实 Chromium 测试隐藏按钮、重复按钮、透明父元素、两个按钮同时出现、延迟显示等情况；不需要任何密码。

### 7.2 只检查真实网页

1. 点 **Actions → VCA Restock Monitor → Run workflow**。
2. mode 选 **dry-run**，点绿色 **Run workflow**。
3. 打开最新记录 → **monitor → Run monitor or test**。
4. 查看输出：
   - `STATUS: IN_STOCK`：检测到了可见的 ADD TO BAG；dry-run 不发送提醒。
   - `STATUS: OUT_OF_STOCK`：只看到 ORDER BY PHONE。
   - `STATUS: UNKNOWN`：两个都不可见，运行会变红，并上传截图。
   - `ERROR`：访问或执行失败，运行会变红。
5. 返回这次运行的摘要页面，向下滚动到 **Artifacts**。
6. 点 `vca-diagnostics-数字-数字` 下载 ZIP，解压打开 `page.png` 和 `result.json`。
7. 看截图是否确实是该款美国商品页面，而不是验证码、Access Denied、地区选择、空白页或 Cookie 遮罩。
8. 识别状态正确后，再手动运行 **check**。它会正常发提醒，如果当时没货则不发。

网页源代码里同时有两个按钮，不能凭抓取文字判断当前库存。本交付没有宣称此刻商品有货。

## 8. 自动运行频率、费用和限制

工作流默认 `7,22,37,52 * * * *`：每小时第 7、22、37、52 分钟计划运行一次，约每 15 分钟一次。使用 UTC；这个频率不需要换算洛杉矶夏令时。计划任务要求配置在仓库默认分支，通常是 main。

GitHub 定时任务不是准时闹钟，可能延迟，高负载时甚至可能丢弃排队任务，无法保证补货后立刻通知。公开仓库长时间无活动（官方目前说明为 60 天）可能自动停用计划任务。详见 [GitHub schedule 文档](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule)。

私有仓库的 Actions 有套餐包含分钟数及计费限制，**不要假定全天监控永久免费**。15 分钟一次约 96 次/天，30 天约 2,880 次；实际计费分钟数还包括安装依赖、浏览器启动等，以你的账户用量为准。

查看方式：GitHub 右上角头像 → **Settings → Billing & licensing**（旧界面可能是 Billing and plans）→ **Usage**，查看 Actions；在 **Budgets and alerts** 中按账户可用选项设置预算与提醒。[GitHub 计费说明](https://docs.github.com/en/billing/concepts/product-billing/github-actions)。

更改频率：

1. 仓库 **Code → .github → workflows → monitor.yml**。
2. 点右上角铅笔 **Edit this file**。
3. 找到 `cron:` 这一行，替换引号内内容：
   - 每 30 分钟：`7,37 * * * *`
   - 每小时：`7 * * * *`
4. 点 **Commit changes… → Commit changes**。

建议先观察几次真实运行和账户用量。官网可能阻挡 GitHub 数据中心 IP；遇到验证码或拒绝访问时，本脚本报失败，不会绕过验证，也不能保证换个时间就解决。

## 9. 购买后暂停／重新启用

暂停：**Actions → VCA Restock Monitor → 右上角 … → Disable workflow**。

重新启用：打开同一工作流页面 → **Enable workflow**。如果页面没有该按钮，查看右上角菜单。

停用不会取消已经开始的运行。如需立即停止，点正在运行的记录 → **Cancel workflow**。

## 10. 常见问题对照

| 现象 | 排查步骤 |
|---|---|
| 看不到 Run workflow | 确认 `.github/workflows/monitor.yml` 路径准确且在默认分支；刷新 Actions 页面 |
| 邮件步骤失败 | 检查三个邮件 Secrets；App Password 是否属于 GMAIL_USER；是否用了普通密码；Google 改密码后是否重新生成 |
| Bark 步骤失败 | BARK_KEY 是否只有 Key；是否用错服务器；重装 App 后 Key 是否变化 |
| Bark 成功但不响 | 在 iPhone 确认重要警告权限和声音；实测静音+睡眠；确认手机联网、Key 属于该设备 |
| UNKNOWN | 下载截图：看按钮是否改名、页面未加载、地区弹窗或验证码；不要直接把 UNKNOWN 改为“没货” |
| ERROR | 下载诊断记录并看失败步骤：浏览器安装/网络/HTTP 拒绝都可能导致；根本未打开页面时可能没有截图 |
| 每 15 分钟都响 | 这是持续有货时的默认行为；购买后停用，或拉长检查间隔 |
| 一路成功，一路失败 | 两路都会独立尝试；整体运行仍标红，需要修好失败的通道 |
| 定时没运行 | 检查工作流是否停用、默认分支、Actions 用量及账单限制；定时服务可能延迟 |
| 找不到截图 | 在运行摘要页 Artifacts 找，不在代码目录找；通知测试模式不创建截图；保留期 7 天 |

## 11. 命令参考（无需零基础用户执行）

```sh
python -m pip install -r requirements.txt
python -m playwright install --with-deps chromium
python monitor.py --test-email
python monitor.py --test-bark
python monitor.py --test-all
python monitor.py --dry-run
python monitor.py
python -m unittest discover -s tests -v
```

在 GitHub 上由工作流自动注入 Secrets。本地手动运行时不会自动取得 GitHub Secrets，必须自行安全地设置对应环境变量；本教程推荐只在 Actions 中运行通知。

## 12. 交付验证范围

本地已做 Python 语法检查，8 项无需网络的逻辑测试全部通过（包括 UNKNOWN 返回 1 并请求截图、通知通道独立失败处理、测试邮件模式与 Bark 参数）。完整浏览器测试代码及 GitHub 手动测试工作流已包含。当前交付环境未能下载 Playwright 依赖，因此**没有完成本地真实 Chromium 测试、VCA 动态页面端到端测试、Gmail 实发或 iPhone 实机响铃测试**。这些分别通过第 6、7 节完成；网页结构未来变化时也需要重新验收。
