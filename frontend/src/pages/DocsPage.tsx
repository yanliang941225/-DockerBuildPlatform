import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { 
  BookOpen, 
  Monitor, 
  Upload, 
  Play, 
  Download, 
  Clock,
  Shield,
  Cpu,
  FileCode,
  Package,
  HardDrive,
  Users,
  HelpCircle,
  ChevronRight,
  ExternalLink,
  Copy,
  Check,
  Layers
} from 'lucide-react';

interface DocSection {
  id: string;
  title: string;
  icon: React.ReactNode;
  content: React.ReactNode;
}

function DocsPage() {
  const [activeSection, setActiveSection] = useState('quickstart');

  const sections: DocSection[] = [
    {
      id: 'quickstart',
      title: '快速开始',
      icon: <Play className="h-5 w-5" />,
      content: <QuickStartContent />,
    },
    {
      id: 'upload',
      title: '文件上传',
      icon: <Upload className="h-5 w-5" />,
      content: <UploadContent />,
    },
    {
      id: 'arch',
      title: '架构说明',
      icon: <Cpu className="h-5 w-5" />,
      content: <ArchContent />,
    },
    {
      id: 'build',
      title: '构建流程',
      icon: <Layers className="h-5 w-5" />,
      content: <BuildContent />,
    },
    {
      id: 'download',
      title: '下载使用',
      icon: <Download className="h-5 w-5" />,
      content: <DownloadContent />,
    },
    {
      id: 'security',
      title: '安全说明',
      icon: <Shield className="h-5 w-5" />,
      content: <SecurityContent />,
    },
    {
      id: 'faq',
      title: '常见问题',
      icon: <HelpCircle className="h-5 w-5" />,
      content: <FAQContent />,
    },
  ];

  const activeContent = sections.find(s => s.id === activeSection)?.content;

  return (
    <div className="container mx-auto max-w-6xl px-4 py-8">
      {/* Header */}
      <div className="mb-8">
        <div className="flex items-center gap-3 mb-2">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-primary/10 text-primary">
            <BookOpen className="h-5 w-5" />
          </div>
          <h1 className="text-2xl font-bold">使用文档</h1>
        </div>
        <p className="text-muted-foreground">
          了解如何使用 Docker 跨架构构建平台
        </p>
      </div>

      <div className="grid lg:grid-cols-[240px_1fr] gap-6">
        {/* Sidebar */}
        <div className="order-2 lg:order-1">
          <Card className="sticky top-20">
            <CardContent className="p-3">
              <nav className="space-y-1">
                {sections.map((section) => (
                  <button
                    key={section.id}
                    onClick={() => setActiveSection(section.id)}
                    className={`
                      w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all
                      ${activeSection === section.id 
                        ? 'bg-primary/10 text-primary' 
                        : 'text-muted-foreground hover:bg-muted hover:text-foreground'
                      }
                    `}
                  >
                    <span className={activeSection === section.id ? 'text-primary' : 'text-muted-foreground'}>
                      {section.icon}
                    </span>
                    {section.title}
                    {activeSection === section.id && (
                      <ChevronRight className="h-4 w-4 ml-auto" />
                    )}
                  </button>
                ))}
              </nav>
            </CardContent>
          </Card>
        </div>

        {/* Content */}
        <div className="order-1 lg:order-2">
          <Card className="animate-fade-in">
            <CardContent className="p-6 lg:p-8">
              {activeContent}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}

// Code Block Component
function CodeBlock({ 
  code, 
  language = 'bash' 
}: { 
  code: string; 
  language?: string;
}) {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="relative group rounded-lg bg-zinc-900 text-zinc-100 my-4">
      <div className="flex items-center justify-between px-4 py-2 border-b border-zinc-800">
        <span className="text-xs text-zinc-500 font-mono">{language}</span>
        <button
          onClick={handleCopy}
          className="text-zinc-400 hover:text-white transition-colors"
        >
          {copied ? (
            <Check className="h-4 w-4 text-emerald-500" />
          ) : (
            <Copy className="h-4 w-4" />
          )}
        </button>
      </div>
      <pre className="p-4 overflow-x-auto text-sm font-mono">
        <code>{code}</code>
      </pre>
    </div>
  );
}

// Info Box Component
function InfoBox({ 
  children, 
  type = 'info' 
}: { 
  children: React.ReactNode; 
  type?: 'info' | 'warning' | 'success' | 'error';
}) {
  const styles = {
    info: 'bg-blue-50 border-blue-200 text-blue-800',
    warning: 'bg-amber-50 border-amber-200 text-amber-800',
    success: 'bg-emerald-50 border-emerald-200 text-emerald-800',
    error: 'bg-red-50 border-red-200 text-red-800',
  };

  const icons = {
    info: <HelpCircle className="h-5 w-5" />,
    warning: <Shield className="h-5 w-5" />,
    success: <Check className="h-5 w-5" />,
    error: <HelpCircle className="h-5 w-5" />,
  };

  return (
    <div className={`flex items-start gap-3 p-4 rounded-lg border my-4 ${styles[type]}`}>
      <span className="shrink-0 mt-0.5">{icons[type]}</span>
      <div className="text-sm leading-relaxed">{children}</div>
    </div>
  );
}

// Section Title Component
function SectionTitle({ 
  children, 
  as: Component = 'h2' 
}: { 
  children: React.ReactNode; 
  as?: 'h2' | 'h3' | 'h4';
}) {
  const classes = {
    h2: 'text-xl font-semibold mb-4',
    h3: 'text-lg font-semibold mb-3',
    h4: 'text-base font-semibold mb-2',
  };
  return <Component className={classes[Component as keyof typeof classes]}>{children}</Component>;
}

// Step Component
function Step({ 
  number, 
  title, 
  children 
}: { 
  number: number; 
  title: string; 
  children: React.ReactNode;
}) {
  return (
    <div className="flex gap-4 mb-6">
      <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-primary text-primary-foreground font-semibold text-sm">
        {number}
      </div>
      <div className="flex-1 pt-1">
        <h3 className="font-semibold mb-2">{title}</h3>
        <div className="text-sm text-muted-foreground">{children}</div>
      </div>
    </div>
  );
}

// Content Components
function QuickStartContent() {
  return (
    <div>
      <h2 className="text-2xl font-bold mb-6 flex items-center gap-3">
        <Play className="h-6 w-6 text-primary" />
        快速开始
      </h2>
      <p className="text-muted-foreground mb-6">
        使用 Docker 跨架构构建平台，只需简单几步即可完成镜像构建。无需注册账号，零配置，即刻使用。
      </p>

      <SectionTitle as="h3">使用流程</SectionTitle>
      
      <Step number={1} title="选择目标架构">
        在构建页面选择您需要的目标架构，支持 X86_64、ARM64、ARMv7 等多种架构。
      </Step>

      <Step number={2} title="上传 Dockerfile">
        上传您的 Dockerfile 文件。系统支持多种命名方式：Dockerfile、.dockerfile、Dockerfile.dev 等。
      </Step>

      <Step number={3} title="上传构建上下文（可选）">
        如果您的 Dockerfile 中使用了 COPY 或 ADD 指令，需要上传包含这些文件的压缩包。
      </Step>

      <Step number={4} title="创建并开始构建">
        点击"创建构建任务"，系统将自动开始构建流程。
      </Step>

      <Step number={5} title="下载镜像">
        构建完成后，点击下载按钮获取您的跨架构镜像。
      </Step>

      <InfoBox type="info">
        构建产物将在 24 小时后自动删除，请及时下载保存。
      </InfoBox>
    </div>
  );
}

function UploadContent() {
  return (
    <div>
      <h2 className="text-2xl font-bold mb-6 flex items-center gap-3">
        <Upload className="h-6 w-6 text-primary" />
        文件上传
      </h2>

      <SectionTitle as="h3">Dockerfile 上传</SectionTitle>
      <p className="text-muted-foreground mb-4">
        上传包含构建指令的 Dockerfile 文件。
      </p>
      <ul className="list-disc list-inside text-sm text-muted-foreground space-y-1 mb-4">
        <li>支持的文件名：Dockerfile、.dockerfile、Dockerfile.dev</li>
        <li>最大文件大小：500MB</li>
        <li>支持拖拽上传或点击选择文件</li>
      </ul>

      <SectionTitle as="h3">构建上下文上传</SectionTitle>
      <p className="text-muted-foreground mb-4">
        如果您的 Dockerfile 中引用了其他文件（如源代码、配置文件等），需要上传包含这些文件的压缩包。
      </p>
      <ul className="list-disc list-inside text-sm text-muted-foreground space-y-1 mb-4">
        <li>支持的格式：.zip、.tar、.tar.gz、.tgz</li>
        <li>最大文件大小：500MB</li>
        <li>压缩包内容将作为构建上下文目录</li>
      </ul>

      <InfoBox type="warning">
        Dockerfile 中使用 COPY 指令时，被拷贝的文件必须在构建上下文目录中存在。如果不上传构建上下文，构建将失败。
      </InfoBox>

      <SectionTitle as="h3">示例 Dockerfile</SectionTitle>
      <CodeBlock
        language="dockerfile"
        code={`# Dockerfile 示例
FROM node:18-alpine

WORKDIR /app

# 复制 package.json
COPY package*.json ./

# 安装依赖
RUN npm ci --only=production

# 复制源代码
COPY . .

# 暴露端口
EXPOSE 3000

# 启动命令
CMD ["node", "server.js"]`}
      />
    </div>
  );
}

function ArchContent() {
  return (
    <div>
      <h2 className="text-2xl font-bold mb-6 flex items-center gap-3">
        <Cpu className="h-6 w-6 text-primary" />
        架构说明
      </h2>

      <p className="text-muted-foreground mb-6">
        Docker Build Platform 使用 Docker BuildKit 实现跨架构构建。构建过程在高性能服务器上完成，支持以下目标架构：
      </p>

      <div className="space-y-4">
        {[
          {
            name: 'X86_64 (AMD64)',
            desc: '传统的 Intel/AMD 处理器架构',
            devices: '传统服务器、Docker Desktop (Intel)、大多数云服务器',
            icon: <Monitor className="h-5 w-5" />,
            color: 'bg-blue-500/10 text-blue-600',
          },
          {
            name: 'ARM64 (AArch64)',
            desc: '64位 ARM 架构',
            devices: 'Apple Silicon Mac、AWS Graviton、树莓派 4B',
            icon: <Package className="h-5 w-5" />,
            color: 'bg-emerald-500/10 text-emerald-600',
          },
          {
            name: 'ARMv7 (ARM32)',
            desc: '32位 ARM 架构',
            devices: '树莓派 2/3、部分嵌入式设备',
            icon: <HardDrive className="h-5 w-5" />,
            color: 'bg-amber-500/10 text-amber-600',
          },
          {
            name: 'ARMv6',
            desc: '32位 ARM v6 架构',
            devices: '树莓派 1、Zero 系列',
            icon: <HardDrive className="h-5 w-5" />,
            color: 'bg-purple-500/10 text-purple-600',
          },
        ].map((arch) => (
          <Card key={arch.name} className="card-interactive">
            <CardContent className="pt-4">
              <div className="flex items-start gap-4">
                <div className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-lg ${arch.color}`}>
                  {arch.icon}
                </div>
                <div>
                  <h3 className="font-semibold">{arch.name}</h3>
                  <p className="text-sm text-muted-foreground mt-0.5">{arch.desc}</p>
                  <p className="text-sm mt-2">
                    <span className="text-muted-foreground">适用设备：</span>
                    {arch.devices}
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      <InfoBox type="info">
        选择目标架构时，请确保您的部署环境与目标架构匹配。例如，在 Apple Silicon Mac 上构建的 ARM64 镜像无法在传统 Intel Mac 上运行。
      </InfoBox>
    </div>
  );
}

function BuildContent() {
  return (
    <div>
      <h2 className="text-2xl font-bold mb-6 flex items-center gap-3">
        <Layers className="h-6 w-6 text-primary" />
        构建流程
      </h2>

      <p className="text-muted-foreground mb-6">
        了解 Docker 镜像构建的完整流程。
      </p>

      <SectionTitle as="h3">构建阶段</SectionTitle>
      
      <div className="space-y-4">
        {[
          {
            stage: '初始化',
            desc: '创建构建任务，初始化构建环境',
            duration: '几秒钟',
          },
          {
            stage: '上传文件',
            desc: '上传 Dockerfile 和构建上下文到服务器',
            duration: '取决于文件大小',
          },
          {
            stage: '安全扫描',
            desc: '检查 Dockerfile 中是否存在危险指令',
            duration: '几秒钟',
          },
          {
            stage: '构建镜像',
            desc: '使用 Docker BuildKit 进行跨架构构建',
            duration: '取决于镜像大小和复杂度',
          },
          {
            stage: '打包上传',
            desc: '将构建完成的镜像打包并上传到存储',
            duration: '取决于镜像大小',
          },
        ].map((item, i) => (
          <div key={i} className="flex items-center gap-4 p-4 rounded-lg bg-muted/30">
            <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-primary/10 text-primary font-semibold text-sm">
              {i + 1}
            </div>
            <div className="flex-1">
              <div className="font-medium">{item.stage}</div>
              <div className="text-sm text-muted-foreground">{item.desc}</div>
            </div>
            <div className="text-sm text-muted-foreground">
              <Clock className="h-4 w-4 inline mr-1" />
              {item.duration}
            </div>
          </div>
        ))}
      </div>

      <SectionTitle as="h3" className="mt-8">构建日志</SectionTitle>
      <p className="text-muted-foreground mb-4">
        构建过程中，您可以实时查看构建日志，了解构建进度和任何潜在问题。
      </p>
      <CodeBlock language="bash" code={`# 典型的构建日志输出
[+] Building 15.3s (2/2) FINISHED
 => [internal] load build definition from Dockerfile
 => [internal] load .dockerignore
 => [1/4] FROM python:3.11-slim
 => [2/4] WORKDIR /app
 => [3/4] COPY requirements.txt .
 => [4/4] RUN pip install -r requirements.txt
 => exporting to image`} />
    </div>
  );
}

function DownloadContent() {
  return (
    <div>
      <h2 className="text-2xl font-bold mb-6 flex items-center gap-3">
        <Download className="h-6 w-6 text-primary" />
        下载使用
      </h2>

      <p className="text-muted-foreground mb-6">
        构建完成后，您可以下载镜像压缩包并加载到本地 Docker 环境中使用。
      </p>

      <SectionTitle as="h3">下载镜像</SectionTitle>
      <p className="text-muted-foreground mb-4">
        在任务详情页或"我的任务"页面，点击"下载镜像"按钮即可下载镜像压缩包。
      </p>

      <SectionTitle as="h3">加载镜像</SectionTitle>
      <p className="text-muted-foreground mb-4">
        下载后，使用以下命令加载镜像：
      </p>
      <CodeBlock language="bash" code={`# 解压镜像文件
tar -xf image.tar.gz

# 加载镜像到 Docker
docker load < image.tar`} />

      <SectionTitle as="h3">运行容器</SectionTitle>
      <p className="text-muted-foreground mb-4">
        镜像加载成功后，使用标准 Docker 命令运行容器：
      </p>
      <CodeBlock language="bash" code={`# 查看已加载的镜像
docker images

# 运行容器
docker run -d -p 8080:3000 --name my-app my-image:latest

# 查看运行状态
docker ps`} />

      <InfoBox type="info">
        下载的镜像文件会在 24 小时后自动删除，请及时加载到本地 Docker 环境。
      </InfoBox>
    </div>
  );
}

function SecurityContent() {
  return (
    <div>
      <h2 className="text-2xl font-bold mb-6 flex items-center gap-3">
        <Shield className="h-6 w-6 text-primary" />
        安全说明
      </h2>

      <p className="text-muted-foreground mb-6">
        Docker Build Platform 采用了多层安全防护措施，保障您的构建安全。
      </p>

      <SectionTitle as="h3">安全检测</SectionTitle>
      <div className="space-y-3">
        {[
          {
            title: 'Dockerfile 安全扫描',
            desc: '自动检测 Dockerfile 中的危险指令，如修改 root 密码、安装未签名包等',
          },
          {
            title: '文件类型验证',
            desc: '验证上传文件的内容类型，防止恶意文件伪装',
          },
          {
            title: '文件大小限制',
            desc: '限制单个文件大小为 500MB，防止资源滥用',
          },
          {
            title: '危险指令检测',
            desc: '检测并阻止包含潜在安全风险指令的构建',
          },
        ].map((item, i) => (
          <div key={i} className="flex items-start gap-3 p-3 rounded-lg bg-muted/30">
            <div className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-emerald-100 text-emerald-600">
              <Check className="h-4 w-4" />
            </div>
            <div>
              <div className="font-medium">{item.title}</div>
              <div className="text-sm text-muted-foreground">{item.desc}</div>
            </div>
          </div>
        ))}
      </div>

      <SectionTitle as="h3" className="mt-8">隐私保护</SectionTitle>
      <ul className="list-disc list-inside text-sm text-muted-foreground space-y-2">
        <li>无需注册账号，保护您的个人信息</li>
        <li>使用浏览器指纹识别会话，无 Cookie 追踪</li>
        <li>构建产物 24 小时后自动删除</li>
        <li>构建日志不保存，仅在构建过程中临时显示</li>
      </ul>

      <SectionTitle as="h3" className="mt-8">环境隔离</SectionTitle>
      <p className="text-muted-foreground">
        每个构建任务在独立的容器环境中执行，与其他任务完全隔离，防止相互影响。
      </p>
    </div>
  );
}

function FAQContent() {
  return (
    <div>
      <h2 className="text-2xl font-bold mb-6 flex items-center gap-3">
        <HelpCircle className="h-6 w-6 text-primary" />
        常见问题
      </h2>

      <div className="space-y-4">
        {[
          {
            q: '为什么需要选择目标架构？',
            a: '不同的服务器和设备使用不同的 CPU 架构。如果镜像架构与设备不匹配，容器将无法运行。通过选择目标架构，我们可以为您构建兼容特定设备的镜像。',
          },
          {
            q: '构建需要多长时间？',
            a: '构建时间取决于镜像大小、Dockerfile 复杂度以及服务器负载。一般简单的镜像需要 1-3 分钟，复杂的镜像可能需要 10 分钟以上。',
          },
          {
            q: '如何加速构建？',
            a: '优化 Dockerfile 是加速构建的关键：使用多阶段构建、减少层数、合理利用缓存、使用更小的基础镜像等。',
          },
          {
            q: '为什么构建失败？',
            a: '常见原因包括：Dockerfile 语法错误、基础镜像不存在或拉取失败、依赖安装失败、COPY 的文件不在上下文中等。请查看构建日志获取详细信息。',
          },
          {
            q: '可以构建 Windows 镜像吗？',
            a: '目前平台仅支持 Linux 容器构建。Windows 容器需要在 Windows Server 环境中构建。',
          },
          {
            q: '镜像下载后如何使用？',
            a: '下载的是镜像压缩包，使用 docker load 命令加载到本地 Docker 环境，然后就可以使用标准的 docker run 命令运行容器了。',
          },
          {
            q: '如何获取构建进度？',
            a: '构建过程中，页面会实时显示构建日志。您也可以在"我的任务"页面查看所有构建任务的状态。',
          },
          {
            q: '任务过期了怎么办？',
            a: '任务过期后，镜像会被自动删除且无法恢复。您需要重新创建任务并执行构建。',
          },
        ].map((item, i) => (
          <Card key={i} className="card-interactive">
            <CardHeader className="pb-2">
              <CardTitle className="text-base flex items-start gap-2">
                <HelpCircle className="h-5 w-5 text-primary shrink-0 mt-0.5" />
                {item.q}
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-muted-foreground">{item.a}</p>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}

export { DocsPage };
export default DocsPage;
