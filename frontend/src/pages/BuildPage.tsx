import { useState, useCallback, useEffect } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import { useToast } from '@/hooks/useToast';
import { apiClient } from '@/lib/api';
import { initSession } from '@/lib/session';
import { useBuildStore, useArchStore } from '@/hooks/useStore';
import { FileUploader } from '@/components/FileUploader';
import { ArchitectureSelector } from '@/components/ArchitectureSelector';
import { BuildStatus } from '@/components/BuildStatus';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Loader2, Plus, Shield, Zap, Clock, Monitor, Cpu, Server } from 'lucide-react';
import type { Architecture, BuildProgress } from '@/types';

const SESSION_KEY = 'build_session_task';

// sessionStorage 持久化的任务状态
interface PersistedTaskState {
  taskId: string;
  dockerfileUploaded: boolean;
  contextUploaded: boolean;
  arch: Architecture;
  imageName: string;
  imageTag: string;
}

export function BuildPage() {
  const { toast } = useToast();
  
  const { 
    currentTask, 
    setCurrentTask, 
    updateTask, 
    setIsBuilding,
    reset 
  } = useBuildStore();
  const { selectedArch, setSelectedArch } = useArchStore();
  
  const [dockerfile, setDockerfile] = useState<File | null>(null);
  const [contextFile, setContextFile] = useState<File | null>(null);
  const [imageName, setImageName] = useState<string>('');
  const [imageTag, setImageTag] = useState<string>('latest');
  const [progress, setProgress] = useState<BuildProgress | null>(null);
  const [sessionReady, setSessionReady] = useState(false);
  const [restoringTask, setRestoringTask] = useState(false);

  // 恢复持久化的任务
  const restorePersistedTask = useCallback(async () => {
    const saved = sessionStorage.getItem(SESSION_KEY);
    if (!saved) return;

    try {
      const savedState: PersistedTaskState = JSON.parse(saved);
      setRestoringTask(true);
      
      // 从服务器获取最新任务状态
      const task = await apiClient.getTask(savedState.taskId);
      
      // 只恢复进行中的任务
      if (task && ['pending', 'uploading', 'building'].includes(task.status)) {
        setCurrentTask(task);
        setSelectedArch(savedState.arch as Architecture);
        setImageName(savedState.imageName);
        setImageTag(savedState.imageTag);
        
        // 如果 Dockerfile 已上传，模拟已上传状态
        if (savedState.dockerfileUploaded) {
          updateTask({ dockerfile_uploaded: true });
        }
        if (savedState.contextUploaded) {
          updateTask({ context_uploaded: true });
        }
        
        toast({
          title: '任务已恢复',
          description: '之前的构建任务已恢复',
        });
      } else {
        // 任务已完成或不存在，清除持久化状态
        sessionStorage.removeItem(SESSION_KEY);
      }
    } catch (error) {
      // 任务获取失败，清除持久化状态
      sessionStorage.removeItem(SESSION_KEY);
      console.error('恢复任务失败:', error);
    } finally {
      setRestoringTask(false);
    }
  }, [setCurrentTask, setSelectedArch, updateTask, toast]);

  // 初始化会话并恢复任务
  useEffect(() => {
    initSession().then((result) => {
      if (result.isInitialized) {
        setSessionReady(true);
        // 尝试恢复持久化的任务
        restorePersistedTask();
      } else {
        setSessionReady(true);
        console.warn('会话初始化失败，但允许继续使用');
      }
    });
  }, [restorePersistedTask]);

  // 保存任务状态到 sessionStorage
  const persistTaskState = useCallback(() => {
    if (!currentTask || currentTask.status === 'building') return;
    
    const state: PersistedTaskState = {
      taskId: currentTask.task_id,
      dockerfileUploaded: currentTask.dockerfile_uploaded,
      contextUploaded: currentTask.context_uploaded,
      arch: selectedArch,
      imageName,
      imageTag,
    };
    sessionStorage.setItem(SESSION_KEY, JSON.stringify(state));
  }, [currentTask, selectedArch, imageName, imageTag]);

  // 监听任务状态变化，保存到 sessionStorage
  useEffect(() => {
    if (currentTask && sessionReady) {
      persistTaskState();
    }
  }, [currentTask?.dockerfile_uploaded, currentTask?.context_uploaded, currentTask?.status, persistTaskState, sessionReady]);

  // Query for task progress
  const { data: progressData } = useQuery({
    queryKey: ['build-progress', currentTask?.task_id],
    queryFn: () => currentTask ? apiClient.getBuildProgress(currentTask.task_id) : null,
    enabled: !!currentTask && (currentTask.status === 'building' || currentTask.status === 'pending'),
    refetchInterval: 2000,
  });

  // Update progress when it changes
  useEffect(() => {
    if (progressData) {
      setProgress(progressData);
    }
  }, [progressData]);

  // Create task mutation
  const createTaskMutation = useMutation({
    mutationFn: (arch: Architecture) => {
      if (!sessionReady) {
        throw new Error('会话初始化中，请稍候');
      }
      return apiClient.createTask(arch, imageName || undefined, imageTag || 'latest');
    },
    onSuccess: (task) => {
      setCurrentTask(task);

      // 创建成功后，自动上传已选择的文件
      if (dockerfile) {
        uploadDockerfileMutation.mutate({ taskId: task.task_id, file: dockerfile });
      }
      if (contextFile) {
        uploadContextMutation.mutate({ taskId: task.task_id, file: contextFile });
      }

      toast({
        title: '任务创建成功',
        description: `任务ID: ${task.task_id.slice(0, 8)}...`,
      });
    },
    onError: (error) => {
      toast({
        title: '创建任务失败',
        description: error instanceof Error ? error.message : '请重试',
        variant: 'destructive',
      });
    },
  });

  // Upload Dockerfile mutation
  const uploadDockerfileMutation = useMutation({
    mutationFn: ({ taskId, file }: { taskId: string; file: File }) =>
      apiClient.uploadDockerfile(taskId, file),
    onSuccess: (data) => {
      updateTask({ dockerfile_uploaded: true });
      toast({
        title: 'Dockerfile 上传成功',
        description: `${data.filename} (${data.size} bytes)`,
      });
    },
    onError: (error) => {
      toast({
        title: '上传失败',
        description: error instanceof Error ? error.message : '请重试',
        variant: 'destructive',
      });
    },
  });

  // Upload context mutation
  const uploadContextMutation = useMutation({
    mutationFn: ({ taskId, file }: { taskId: string; file: File }) =>
      apiClient.uploadContext(taskId, file),
    onSuccess: (data) => {
      updateTask({ context_uploaded: true });
      toast({
        title: '上下文文件上传成功',
        description: `${data.filename} (${data.size} bytes)`,
      });
    },
    onError: (error) => {
      toast({
        title: '上传失败',
        description: error instanceof Error ? error.message : '请重试',
        variant: 'destructive',
      });
    },
  });

  // Start build mutation
  const startBuildMutation = useMutation({
    mutationFn: (taskId: string) => apiClient.startBuild(taskId),
    onMutate: () => {
      setIsBuilding(true);
    },
    onSuccess: () => {
      // 清除持久化状态，构建已完成或失败
      sessionStorage.removeItem(SESSION_KEY);
      toast({
        title: '构建已启动',
        description: '正在准备构建环境...',
      });
    },
    onError: (error) => {
      setIsBuilding(false);
      toast({
        title: '启动失败',
        description: error instanceof Error ? error.message : '请重试',
        variant: 'destructive',
      });
    },
  });

  // Delete task mutation
  const deleteTaskMutation = useMutation({
    mutationFn: (taskId: string) => apiClient.deleteTask(taskId),
    onSuccess: () => {
      reset();
      setDockerfile(null);
      setContextFile(null);
      sessionStorage.removeItem(SESSION_KEY);
      toast({
        title: '任务已删除',
      });
    },
    onError: (error) => {
      toast({
        title: '删除失败',
        description: error instanceof Error ? error.message : '请重试',
        variant: 'destructive',
      });
    },
  });

  // Handle Dockerfile selection
  const handleDockerfileSelect = useCallback(async (file: File | null) => {
    setDockerfile(file);
    
    if (file && currentTask) {
      uploadDockerfileMutation.mutate({ taskId: currentTask.task_id, file });
    }
  }, [currentTask, uploadDockerfileMutation]);

  // Handle context selection
  const handleContextSelect = useCallback(async (file: File | null) => {
    setContextFile(file);
    
    if (file && currentTask) {
      uploadContextMutation.mutate({ taskId: currentTask.task_id, file });
    }
  }, [currentTask, uploadContextMutation]);

  // Create new task
  const handleCreateTask = () => {
    createTaskMutation.mutate(selectedArch);
  };

  // Start build
  const handleStartBuild = () => {
    if (currentTask) {
      startBuildMutation.mutate(currentTask.task_id);
    }
  };

  // Download
  const handleDownload = () => {
    if (currentTask?.download_url) {
      window.open(currentTask.download_url, '_blank');
    }
  };

  // Delete task
  const handleDelete = () => {
    if (currentTask) {
      deleteTaskMutation.mutate(currentTask.task_id);
    }
  };

  // Reset
  const handleReset = () => {
    reset();
    setDockerfile(null);
    setContextFile(null);
    setImageName('');
    setImageTag('latest');
    setProgress(null);
    // 清除持久化的任务状态
    sessionStorage.removeItem(SESSION_KEY);
  };

  return (
    <div className="container mx-auto max-w-5xl px-4 py-8">
      {/* Hero Section */}
      {!currentTask && (
        <div className="mb-12 text-center animate-fade-in">
          <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-primary/10 text-primary text-sm font-medium mb-6">
            <span className="relative flex h-2 w-2">
              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-primary opacity-75"></span>
              <span className="relative inline-flex h-2 w-2 rounded-full bg-primary"></span>
            </span>
            在线服务
          </div>
          <h1 className="text-4xl md:text-5xl font-bold tracking-tight mb-4">
            <span className="gradient-text">Docker 跨架构构建</span>
          </h1>
          <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
            无需配置环境，一键构建多平台 Docker 镜像。支持 X86、ARM64、ARMv7 等主流架构
          </p>
        </div>
      )}

      {/* 恢复中的提示 */}
      {restoringTask && (
        <Card className="mb-6 border-primary/20 bg-primary/5">
          <CardContent className="py-4 flex items-center justify-center gap-3">
            <Loader2 className="h-5 w-5 animate-spin text-primary" />
            <span className="text-sm">正在恢复之前的构建任务...</span>
          </CardContent>
        </Card>
      )}

      {!currentTask ? (
        // Setup Phase
        <div className="space-y-6">
          <Card className="card-interactive">
            <CardHeader className="pb-4">
              <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-primary to-blue-500 text-white">
                  <Server className="h-5 w-5" />
                </div>
                <div>
                  <CardTitle className="text-lg">配置构建任务</CardTitle>
                  <CardDescription>选择目标架构并上传必要的文件</CardDescription>
                </div>
              </div>
            </CardHeader>
            <CardContent className="space-y-8">
              {/* Architecture Selection */}
              <div>
                <label className="mb-4 block text-sm font-medium flex items-center gap-2">
                  <Cpu className="h-4 w-4 text-primary" />
                  选择目标架构
                </label>
                <ArchitectureSelector
                  selected={selectedArch}
                  onSelect={setSelectedArch}
                />
              </div>

              {/* Image Name and Tag */}
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                <div className="space-y-2">
                  <label className="text-sm font-medium">
                    镜像名称 <span className="text-muted-foreground font-normal">(可选)</span>
                  </label>
                  <Input
                    type="text"
                    placeholder="my-app"
                    value={imageName}
                    onChange={(e) => setImageName(e.target.value)}
                    className="h-11"
                  />
                  <p className="text-xs text-muted-foreground">
                    用于命名构建的镜像
                  </p>
                </div>
                <div className="space-y-2">
                  <label className="text-sm font-medium">
                    镜像版本 <span className="text-muted-foreground font-normal">(可选)</span>
                  </label>
                  <Input
                    type="text"
                    placeholder="latest"
                    value={imageTag}
                    onChange={(e) => setImageTag(e.target.value)}
                    className="h-11"
                  />
                  <p className="text-xs text-muted-foreground">
                    默认为 latest
                  </p>
                </div>
              </div>

              {/* Dockerfile Upload */}
              <div className="space-y-3">
                <label className="text-sm font-medium flex items-center gap-2">
                  <Monitor className="h-4 w-4 text-primary" />
                  上传 Dockerfile
                  <span className="text-destructive">*</span>
                </label>
                <FileUploader
                  allowedExtensions={['Dockerfile', '.dockerfile', '.Dockerfile', 'Dockerfile.dev']}
                  onFileSelect={handleDockerfileSelect}
                  selectedFile={dockerfile}
                  title="拖拽 Dockerfile 到这里"
                  description="支持: Dockerfile, .dockerfile, Dockerfile.dev"
                />
              </div>

              {/* Context Upload (Optional) */}
              <div className="space-y-3">
                <label className="text-sm font-medium flex items-center gap-2">
                  <Server className="h-4 w-4 text-primary" />
                  构建上下文 <span className="text-muted-foreground font-normal">(可选)</span>
                </label>
                <FileUploader
                  allowedExtensions={['.zip', '.tar', '.tar.gz', '.tgz']}
                  onFileSelect={handleContextSelect}
                  selectedFile={contextFile}
                  title="拖拽上下文文件到这里"
                  description="支持: .zip, .tar, .tar.gz, .tgz"
                />
                <p className="flex items-start gap-2 text-xs text-muted-foreground bg-muted/30 p-3 rounded-lg">
                  <span className="text-primary mt-0.5">💡</span>
                  如果您的 Dockerfile 中使用了 COPY 或 ADD 指令引用了其他文件，请上传包含这些文件的压缩包作为构建上下文。
                </p>
              </div>

              {/* Start Button */}
              <div className="pt-4">
                <Button
                  size="lg"
                  onClick={handleCreateTask}
                  disabled={createTaskMutation.isPending || !sessionReady}
                  className="w-full sm:w-auto h-12 px-8 text-base shadow-lg shadow-primary/25"
                >
                  {!sessionReady ? (
                    <>
                      <Loader2 className="mr-2 h-5 w-5 animate-spin" />
                      初始化中...
                    </>
                  ) : createTaskMutation.isPending ? (
                    <>
                      <Loader2 className="mr-2 h-5 w-5 animate-spin" />
                      创建中...
                    </>
                  ) : (
                    <>
                      <Plus className="mr-2 h-5 w-5" />
                      创建构建任务
                    </>
                  )}
                </Button>
              </div>
            </CardContent>
          </Card>

          {/* Features Section */}
          <div className="grid gap-4 md:grid-cols-3">
            <Card className="card-interactive group">
              <CardContent className="pt-6">
                <div className="flex items-start gap-4">
                  <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-emerald-500/10 text-emerald-600 group-hover:scale-110 transition-transform">
                    <Shield className="h-6 w-6" />
                  </div>
                  <div>
                    <h3 className="font-semibold mb-1">安全可靠</h3>
                    <p className="text-sm text-muted-foreground">
                      Dockerfile 安全扫描，危险指令检测，构建环境隔离
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card className="card-interactive group">
              <CardContent className="pt-6">
                <div className="flex items-start gap-4">
                  <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-blue-500/10 text-blue-600 group-hover:scale-110 transition-transform">
                    <Zap className="h-6 w-6" />
                  </div>
                  <div>
                    <h3 className="font-semibold mb-1">简单快捷</h3>
                    <p className="text-sm text-muted-foreground">
                      无需注册，上传即用，实时查看构建进度
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card className="card-interactive group">
              <CardContent className="pt-6">
                <div className="flex items-start gap-4">
                  <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-amber-500/10 text-amber-600 group-hover:scale-110 transition-transform">
                    <Clock className="h-6 w-6" />
                  </div>
                  <div>
                    <h3 className="font-semibold mb-1">自动清理</h3>
                    <p className="text-sm text-muted-foreground">
                      24小时后自动删除，保护您的隐私和数据安全
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Supported Architectures */}
          <Card>
            <CardContent className="pt-6">
              <h3 className="font-semibold mb-4 flex items-center gap-2">
                <Cpu className="h-4 w-4 text-primary" />
                支持的架构
              </h3>
              <div className="flex flex-wrap gap-3">
                {[
                  { name: 'X86_64', desc: 'Intel / AMD' },
                  { name: 'ARM64', desc: 'Apple Silicon / AWS Graviton' },
                  { name: 'ARMv7', desc: 'Raspberry Pi 2/3/4' },
                  { name: 'ARMv6', desc: 'Raspberry Pi 1 / Zero' },
                ].map((arch) => (
                  <div 
                    key={arch.name}
                    className="px-4 py-2 rounded-lg bg-muted/50 border border-border/50 text-sm"
                  >
                    <span className="font-medium">{arch.name}</span>
                    <span className="text-muted-foreground ml-2">{arch.desc}</span>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </div>
      ) : (
        // Build Phase
        <div className="space-y-6">
          {/* Build Status */}
          <BuildStatus
            task={currentTask}
            progress={progressData || progress}
            onStartBuild={handleStartBuild}
            onDownload={handleDownload}
            onDelete={handleDelete}
            onReset={handleReset}
            canStartBuild={
              ['pending'].includes(currentTask.status) &&
              currentTask.dockerfile_uploaded
            }
            isStarting={startBuildMutation.isPending}
          />
        </div>
      )}
    </div>
  );
}
