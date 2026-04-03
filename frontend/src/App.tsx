import { useState } from 'react';
import { BuildPage } from '@/pages/BuildPage';
import { MyTasksPage } from '@/pages/MyTasksPage';
import { DocsPage } from '@/pages/DocsPage';
import { Toaster } from '@/components/ui/toaster';
import { 
  Layers, 
  FileText, 
  Github, 
  Menu, 
  X
} from 'lucide-react';

type PageType = 'build' | 'my-tasks' | 'docs';

function App() {
  const [currentPage, setCurrentPage] = useState<PageType>('build');
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const navItems = [
    { id: 'build' as const, label: '开始构建', icon: Layers },
    { id: 'my-tasks' as const, label: '我的任务', icon: null },
    { id: 'docs' as const, label: '使用文档', icon: FileText },
  ];

  return (
    <div className="min-h-screen bg-gradient-subtle">
      {/* Background Decoration */}
      <div className="fixed inset-0 -z-10 overflow-hidden">
        <div className="absolute top-0 left-1/4 w-[500px] h-[500px] bg-primary/5 rounded-full blur-3xl" />
        <div className="absolute bottom-0 right-1/4 w-[400px] h-[400px] bg-blue-400/5 rounded-full blur-3xl" />
      </div>

      {/* Header */}
      <header className="sticky top-0 z-50 backdrop-blur-xl bg-background/80 border-b border-border/50">
        <div className="container mx-auto">
          <div className="flex h-16 items-center justify-between px-4 lg:px-6">
            {/* Logo */}
            <button 
              onClick={() => setCurrentPage('build')}
              className="flex items-center gap-3 group"
            >
              <div className="relative">
                <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-primary via-blue-600 to-cyan-500 text-white font-bold text-lg shadow-lg shadow-primary/25 group-hover:shadow-primary/40 transition-shadow duration-300">
                  D
                </div>
                <div className="absolute -bottom-0.5 -right-0.5 h-3 w-3 bg-emerald-500 rounded-full border-2 border-background animate-pulse" />
              </div>
              <div className="hidden sm:block">
                <div className="text-sm font-semibold tracking-tight">Docker Build</div>
                <div className="text-[10px] text-muted-foreground -mt-0.5">跨架构镜像构建</div>
              </div>
            </button>

            {/* Desktop Navigation */}
            <nav className="hidden md:flex items-center gap-1">
              {navItems.map((item) => (
                <button
                  key={item.id}
                  onClick={() => setCurrentPage(item.id)}
                  className={`
                    relative px-4 py-2 text-sm font-medium rounded-lg transition-all duration-200
                    ${currentPage === item.id 
                      ? 'text-primary bg-primary/10' 
                      : 'text-muted-foreground hover:text-foreground hover:bg-muted/50'
                    }
                  `}
                >
                  <span className="flex items-center gap-2">
                    {item.icon && <item.icon className="h-4 w-4" />}
                    {item.label}
                  </span>
                  {currentPage === item.id && (
                    <span className="absolute bottom-0 left-1/2 -translate-x-1/2 w-6 h-0.5 bg-primary rounded-full" />
                  )}
                </button>
              ))}
            </nav>

            {/* Right Actions */}
            <div className="flex items-center gap-3">
              <a
                href="https://github.com/yanliang941225/-DockerBuildPlatform"
                target="_blank"
                rel="noopener noreferrer"
                className="hidden sm:flex items-center gap-2 px-3 py-1.5 text-sm text-muted-foreground hover:text-foreground rounded-lg hover:bg-muted/50 transition-colors"
              >
                <Github className="h-4 w-4" />
                <span>GitHub</span>
              </a>
              
              {/* Mobile Menu Button */}
              <button
                onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
                className="md:hidden p-2 rounded-lg hover:bg-muted/50 transition-colors"
              >
                {mobileMenuOpen ? (
                  <X className="h-5 w-5" />
                ) : (
                  <Menu className="h-5 w-5" />
                )}
              </button>
            </div>
          </div>

          {/* Mobile Navigation */}
          {mobileMenuOpen && (
            <div className="md:hidden border-t border-border/50 py-3 px-4 animate-fade-in">
              <div className="flex flex-col gap-1">
                {navItems.map((item) => (
                  <button
                    key={item.id}
                    onClick={() => {
                      setCurrentPage(item.id);
                      setMobileMenuOpen(false);
                    }}
                    className={`
                      flex items-center gap-3 px-4 py-3 text-sm font-medium rounded-lg transition-colors
                      ${currentPage === item.id 
                        ? 'text-primary bg-primary/10' 
                        : 'text-muted-foreground hover:text-foreground hover:bg-muted/50'
                      }
                    `}
                  >
                    {item.icon && <item.icon className="h-4 w-4" />}
                    {item.label}
                  </button>
                ))}
                <a
                  href="https://github.com/yanliang941225/-DockerBuildPlatform"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center gap-3 px-4 py-3 text-sm text-muted-foreground hover:text-foreground rounded-lg hover:bg-muted/50 transition-colors"
                >
                  <Github className="h-4 w-4" />
                  GitHub
                </a>
              </div>
            </div>
          )}
        </div>
      </header>

      {/* Main Content */}
      <main className="animate-fade-in">
        {currentPage === 'build' && <BuildPage />}
        {currentPage === 'my-tasks' && <MyTasksPage />}
        {currentPage === 'docs' && <DocsPage />}
      </main>

      {/* Footer */}
      <footer className="mt-auto border-t border-border/50 bg-muted/20">
        <div className="container mx-auto px-4 py-8">
          <div className="grid gap-8 md:grid-cols-3">
            {/* Brand */}
            <div>
              <div className="flex items-center gap-2 mb-3">
                <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-primary to-cyan-500 text-white font-bold text-sm">
                  D
                </div>
                <span className="font-semibold">Docker Build Platform</span>
              </div>
              <p className="text-sm text-muted-foreground leading-relaxed">
                安全可靠的 Docker 跨架构镜像构建服务，支持多种处理器架构。
              </p>
            </div>

            {/* Quick Links */}
            <div>
              <h4 className="text-sm font-semibold mb-3">快速链接</h4>
              <div className="space-y-2">
                <button 
                  onClick={() => setCurrentPage('build')}
                  className="block text-sm text-muted-foreground hover:text-foreground transition-colors"
                >
                  开始构建
                </button>
                <button 
                  onClick={() => setCurrentPage('docs')}
                  className="block text-sm text-muted-foreground hover:text-foreground transition-colors"
                >
                  使用文档
                </button>
                <a 
                  href="https://github.com/yanliang941225/-DockerBuildPlatform"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="block text-sm text-muted-foreground hover:text-foreground transition-colors"
                >
                  GitHub
                </a>
              </div>
            </div>

            {/* Info */}
            <div>
              <h4 className="text-sm font-semibold mb-3">服务说明</h4>
              <div className="space-y-2 text-sm text-muted-foreground">
                <div className="flex items-center gap-2">
                  <div className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
                  <span>构建产物将在 24 小时后自动删除</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="h-1.5 w-1.5 rounded-full bg-blue-500" />
                  <span>支持多架构跨平台构建</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="h-1.5 w-1.5 rounded-full bg-amber-500" />
                  <span>无需注册，即刻使用</span>
                </div>
              </div>
            </div>
          </div>

          {/* Bottom */}
          <div className="mt-8 pt-6 border-t border-border/50 flex flex-col sm:flex-row items-center justify-between gap-4">
            <p className="text-sm text-muted-foreground">
              Docker 跨架构构建平台 - 安全、简单、快捷
            </p>
            <p className="text-sm text-muted-foreground/70">
              构建产物将在 24 小时后自动删除，请及时下载
            </p>
          </div>
        </div>
      </footer>

      {/* Toast Container */}
      <Toaster />
    </div>
  );
}

export default App;
