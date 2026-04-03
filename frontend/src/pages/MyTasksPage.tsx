import { useEffect, useState, useCallback } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import { apiClient } from '@/lib/api';
import { initSession } from '@/lib/session';
import { useToast } from '@/hooks/useToast';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';
import { BuildLogs } from '@/components/BuildLogs';
import { 
  Loader2, 
  Clock, 
  RefreshCw, 
  FileText, 
  Download, 
  ChevronDown, 
  ChevronUp,
  Trash2,
  Activity,
  CheckCircle2,
  XCircle,
  Inbox,
  Cpu
} from 'lucide-react';
import { STATUS_INFO } from '@/types';
import { formatTimeRemaining, formatDateTime, cn } from '@/lib/utils';
import type { Task, LogEntry } from '@/types';

export function MyTasksPage() {
  const { toast } = useToast();
  const [sessionReady, setSessionReady] = useState(false);

  // 初始化会话
  useEffect(() => {
    initSession().then((result) => {
      setSessionReady(result.isInitialized);
    });
  }, []);

  // 获取我的任务列表
  const { data, isLoading, refetch, isFetching } = useQuery({
    queryKey: ['my-tasks'],
    queryFn: () => apiClient.getMyTasks(100, 0),
    enabled: sessionReady,
  });

  // 当会话就绪时，触发一次查询
  useEffect(() => {
    if (sessionReady) {
      refetch();
    }
  }, [sessionReady]);

  // 删除任务
  const deleteMutation = useMutation({
    mutationFn: (taskId: string) => apiClient.deleteTask(taskId),
    onSuccess: () => {
      toast({ title: '任务已删除' });
      refetch();
    },
    onError: (error) => {
      toast({
        title: '删除失败',
        description: error instanceof Error ? error.message : '请重试',
        variant: 'destructive',
      });
    },
  });

  const tasks = data?.tasks || [];
  const activeTasks = tasks.filter(t => !['success', 'failed', 'expired', 'cancelled'].includes(t.status));
  const completedTasks = tasks.filter(t => ['success', 'failed'].includes(t.status));

  return (
    <div className="container mx-auto max-w-5xl px-4 py-8">
      {/* Header */}
      <div className="mb-8">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold flex items-center gap-3">
              <Activity className="h-6 w-6 text-primary" />
              我的构建任务
            </h1>
            <p className="text-muted-foreground mt-1">查看和管理您的 Docker 镜像构建任务</p>
          </div>
          <Button
            variant="outline"
            size="sm"
            onClick={() => refetch()}
            disabled={isFetching}
            className="self-start"
          >
            <RefreshCw className={cn("h-4 w-4 mr-2", isFetching && "animate-spin")} />
            刷新列表
          </Button>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid gap-4 md:grid-cols-4 mb-8">
        <Card className="card-interactive">
          <CardContent className="pt-6">
            <div className="flex items-center gap-4">
              <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-muted text-muted-foreground">
                <Inbox className="h-6 w-6" />
              </div>
              <div>
                <div className="text-2xl font-bold">{tasks.length}</div>
                <div className="text-sm text-muted-foreground">总任务数</div>
              </div>
            </div>
          </CardContent>
        </Card>
        
        <Card className="card-interactive">
          <CardContent className="pt-6">
            <div className="flex items-center gap-4">
              <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-blue-500/10 text-blue-600">
                <Activity className="h-6 w-6" />
              </div>
              <div>
                <div className="text-2xl font-bold text-blue-600">{activeTasks.length}</div>
                <div className="text-sm text-muted-foreground">进行中</div>
              </div>
            </div>
          </CardContent>
        </Card>
        
        <Card className="card-interactive">
          <CardContent className="pt-6">
            <div className="flex items-center gap-4">
              <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-emerald-500/10 text-emerald-600">
                <CheckCircle2 className="h-6 w-6" />
              </div>
              <div>
                <div className="text-2xl font-bold text-emerald-600">
                  {completedTasks.filter(t => t.status === 'success').length}
                </div>
                <div className="text-sm text-muted-foreground">构建成功</div>
              </div>
            </div>
          </CardContent>
        </Card>
        
        <Card className="card-interactive">
          <CardContent className="pt-6">
            <div className="flex items-center gap-4">
              <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-red-500/10 text-red-600">
                <XCircle className="h-6 w-6" />
              </div>
              <div>
                <div className="text-2xl font-bold text-red-600">
                  {completedTasks.filter(t => t.status === 'failed').length}
                </div>
                <div className="text-sm text-muted-foreground">构建失败</div>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Task List */}
      {isLoading ? (
        <div className="flex flex-col items-center justify-center py-16">
          <Loader2 className="h-8 w-8 animate-spin text-primary mb-4" />
          <p className="text-muted-foreground">加载任务列表...</p>
        </div>
      ) : tasks.length === 0 ? (
        <Card>
          <CardContent className="py-16 text-center">
            <div className="flex h-16 w-16 mx-auto items-center justify-center rounded-full bg-muted mb-4">
              <Inbox className="h-8 w-8 text-muted-foreground" />
            </div>
            <h3 className="text-lg font-semibold mb-2">暂无构建任务</h3>
            <p className="text-muted-foreground mb-6">创建一个新任务开始构建镜像</p>
            <Button asChild>
              <a href="#" onClick={(e) => { e.preventDefault(); window.location.hash = ''; }}>
                前往构建页面
              </a>
            </Button>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-6">
          {/* 进行中的任务 */}
          {activeTasks.length > 0 && (
            <div>
              <h2 className="text-lg font-semibold mb-4 flex items-center gap-3">
                <span className="relative flex h-2.5 w-2.5">
                  <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-blue-400 opacity-75"></span>
                  <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-blue-500"></span>
                </span>
                进行中 ({activeTasks.length})
              </h2>
              <div className="space-y-4">
                {activeTasks.map((task) => (
                  <TaskCard
                    key={task.task_id}
                    task={task}
                    onDelete={() => deleteMutation.mutate(task.task_id)}
                    isDeleting={deleteMutation.isPending}
                  />
                ))}
              </div>
            </div>
          )}

          {/* 已完成的任务 */}
          {completedTasks.length > 0 && (
            <div>
              <h2 className="text-lg font-semibold mb-4 flex items-center gap-3">
                <CheckCircle2 className="h-5 w-5 text-muted-foreground" />
                已完成 ({completedTasks.length})
              </h2>
              <div className="space-y-4">
                {completedTasks.map((task) => (
                  <TaskCard
                    key={task.task_id}
                    task={task}
                    onDelete={() => deleteMutation.mutate(task.task_id)}
                    isDeleting={deleteMutation.isPending}
                  />
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// 任务卡片组件
interface TaskCardProps {
  task: Task;
  onDelete: () => void;
  isDeleting: boolean;
}

function TaskCard({ task, onDelete, isDeleting }: TaskCardProps) {
  const [showLogs, setShowLogs] = useState(false);
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [logsLoading, setLogsLoading] = useState(false);

  const statusInfo = STATUS_INFO[task.status];
  const timeRemaining = formatTimeRemaining(task.expires_at);
  const isBuilding = task.status === 'building';

  // 加载日志
  const loadLogs = useCallback(async () => {
    setLogsLoading(true);
    try {
      const response = await apiClient.getBuildLogs(task.task_id);
      setLogs(response.logs.map(log => ({
        timestamp: typeof log.timestamp === 'string' ? log.timestamp : new Date(log.timestamp).toISOString(),
        level: log.level,
        message: log.message,
      })));
    } catch (error) {
      console.error('加载日志失败:', error);
    } finally {
      setLogsLoading(false);
    }
  }, [task.task_id]);

  // 构建中的任务定期刷新日志
  useEffect(() => {
    if (!showLogs || !isBuilding) return;
    
    loadLogs();
    const interval = setInterval(loadLogs, 3000);
    
    return () => clearInterval(interval);
  }, [showLogs, isBuilding, loadLogs]);

  // 切换日志显示
  const toggleLogs = async () => {
    if (!showLogs) {
      await loadLogs();
    }
    setShowLogs(!showLogs);
  };

  // 下载镜像
  const handleDownload = () => {
    if (task.download_url) {
      window.open(task.download_url, '_blank');
    }
  };

  return (
    <Card className={cn(
      "card-interactive transition-all",
      task.status === 'building' && "border-blue-200 bg-blue-50/30",
      task.status === 'success' && "border-emerald-200 bg-emerald-50/30",
      task.status === 'failed' && "border-red-200 bg-red-50/30"
    )}>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div className={cn(
              "flex h-10 w-10 items-center justify-center rounded-xl text-lg",
              task.status === 'building' && "bg-blue-100 text-blue-600",
              task.status === 'success' && "bg-emerald-100 text-emerald-600",
              task.status === 'failed' && "bg-red-100 text-red-600",
              ['pending', 'uploading'].includes(task.status) && "bg-amber-100 text-amber-600",
              !['building', 'success', 'failed', 'pending', 'uploading'].includes(task.status) && "bg-muted text-muted-foreground"
            )}>
              {statusInfo.icon}
            </div>
            <div>
              <CardTitle className={cn("text-base flex items-center gap-2", statusInfo.color)}>
                {statusInfo.label}
                {isBuilding && (
                  <span className="relative flex h-2 w-2">
                    <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-blue-400 opacity-75"></span>
                    <span className="relative inline-flex h-2 w-2 rounded-full bg-blue-500"></span>
                  </span>
                )}
              </CardTitle>
              <div className="flex items-center gap-2 mt-0.5">
                <code className="text-xs text-muted-foreground bg-muted px-2 py-0.5 rounded">
                  {task.task_id.slice(0, 8)}...{task.task_id.slice(-4)}
                </code>
                <span className="text-xs text-muted-foreground">•</span>
                <div className="flex items-center gap-1 text-xs text-muted-foreground">
                  <Cpu className="h-3 w-3" />
                  {task.target_arch}
                </div>
              </div>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-1.5 text-sm text-muted-foreground">
              <Clock className="h-4 w-4" />
              <span>{timeRemaining}</span>
            </div>
          </div>
        </div>
      </CardHeader>
      
      <CardContent>
        {/* Info Grid */}
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4 text-sm mb-4">
          <div className="flex items-center gap-2 p-2 rounded-lg bg-muted/30">
            <span className="text-muted-foreground">镜像:</span>
            <span className="font-medium truncate">
              {task.image_name || '未命名'}:{task.image_tag || 'latest'}
            </span>
          </div>
          <div className="flex items-center gap-2 p-2 rounded-lg bg-muted/30">
            <span className="text-muted-foreground">创建:</span>
            <span>{formatDateTime(task.created_at)}</span>
          </div>
          <div className="flex items-center gap-2 p-2 rounded-lg bg-muted/30">
            <span className="text-muted-foreground">Dockerfile:</span>
            <span className={cn(
              "font-medium",
              task.dockerfile_uploaded ? "text-emerald-600" : "text-amber-600"
            )}>
              {task.dockerfile_uploaded ? "已上传 ✓" : "未上传"}
            </span>
          </div>
          <div className="flex items-center gap-2 p-2 rounded-lg bg-muted/30">
            <span className="text-muted-foreground">上下文:</span>
            <span className={cn(
              "font-medium",
              task.context_uploaded ? "text-emerald-600" : "text-muted-foreground"
            )}>
              {task.context_uploaded ? "已上传 ✓" : "未上传"}
            </span>
          </div>
        </div>

        {/* Progress Bar for Building */}
        {task.status === 'building' && (
          <div className="mb-4">
            <Progress value={50} className="h-2 progress-gradient" />
            <p className="text-xs text-muted-foreground mt-2 flex items-center gap-1">
              <Activity className="h-3 w-3 animate-pulse" />
              正在构建中，请稍候...
            </p>
          </div>
        )}

        {/* 错误信息 */}
        {task.error_message && (
          <div className="mb-4 p-3 rounded-lg bg-red-50 border border-red-200 text-sm text-red-700">
            <div className="flex items-start gap-2">
              <XCircle className="h-4 w-4 mt-0.5 shrink-0" />
              <div>
                <span className="font-medium">构建失败:</span>
                <p className="mt-1">{task.error_message}</p>
              </div>
            </div>
          </div>
        )}

        {/* Action Buttons */}
        <div className="flex flex-wrap items-center gap-2">
          {/* Download for Success */}
          {task.status === 'success' && task.download_url && (
            <Button size="sm" onClick={handleDownload} className="shadow-sm">
              <Download className="h-4 w-4 mr-2" />
              下载镜像
            </Button>
          )}

          {/* View Logs */}
          <Button
            variant="outline"
            size="sm"
            onClick={toggleLogs}
            disabled={logsLoading}
          >
            {logsLoading ? (
              <Loader2 className="h-4 w-4 animate-spin mr-2" />
            ) : (
              <FileText className="h-4 w-4 mr-2" />
            )}
            {showLogs ? '收起' : '查看日志'}
            {showLogs ? <ChevronUp className="h-4 w-4 ml-2" /> : <ChevronDown className="h-4 w-4 ml-2" />}
          </Button>

          {/* Delete */}
          <Button
            variant="outline"
            size="sm"
            onClick={onDelete}
            disabled={isDeleting || task.status === 'building'}
            className="text-destructive hover:text-destructive hover:border-destructive/50"
          >
            {isDeleting ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Trash2 className="h-4 w-4 mr-2" />
            )}
            删除
          </Button>
        </div>

        {/* Logs Section */}
        {showLogs && (
          <div className="mt-4">
            <BuildLogs logs={logs} isBuilding={task.status === 'building'} />
          </div>
        )}
      </CardContent>
    </Card>
  );
}
