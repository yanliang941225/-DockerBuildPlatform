import { useState, useCallback } from 'react';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { BuildLogs } from '@/components/BuildLogs';
import { 
  Download, 
  Trash2,
  RefreshCw,
  Loader2,
  Clock,
  AlertTriangle,
  FileCode,
  FolderArchive,
  Bug,
  ChevronUp
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { formatTimeRemaining, formatDateTime } from '@/lib/utils';
import { STATUS_INFO } from '@/types';
import type { Task, BuildProgress } from '@/types';
import { apiClient } from '@/lib/api';

interface BuildStatusProps {
  task: Task;
  progress: BuildProgress | null;
  onStartBuild: () => void;
  onDownload: () => void;
  onDelete: () => void;
  onReset: () => void;
  isStarting: boolean;
  // 是否正在上传文件
  isUploading?: boolean;
}

export function BuildStatus({
  task,
  progress,
  onStartBuild,
  onDownload,
  onDelete,
  onReset,
  isStarting,
  isUploading = false,
}: BuildStatusProps) {
  const statusInfo = STATUS_INFO[task.status];
  const isBuilding = task.status === 'building' || task.status === 'uploading';
  const isSuccess = task.status === 'success';
  const isFailed = task.status === 'failed';
  const timeRemaining = formatTimeRemaining(task.expires_at);

  // 调试状态
  const [showDebug, setShowDebug] = useState(false);
  const [storageInfo, setStorageInfo] = useState<any>(null);
  const [debugLoading, setDebugLoading] = useState(false);

  // 加载存储调试信息
  const loadStorageDebug = useCallback(async () => {
    setDebugLoading(true);
    try {
      const [info, files] = await Promise.all([
        apiClient.getStorageInfo(),
        apiClient.listStorageFiles('uploads/' + task.task_id)
      ]);
      setStorageInfo({ info, files });
    } catch (e) {
      console.error('加载调试信息失败:', e);
    } finally {
      setDebugLoading(false);
    }
  }, [task.task_id]);

  // 切换调试信息显示
  const toggleDebug = useCallback(async () => {
    if (!showDebug && !storageInfo) {
      await loadStorageDebug();
    }
    setShowDebug(!showDebug);
  }, [showDebug, storageInfo, loadStorageDebug]);

  // 构建按钮是否可用：
  // 1. Dockerfile 必须已上传
  // 2. 任务状态必须是 pending
  // 3. 没有文件正在上传中
  const canActuallyStartBuild = task.dockerfile_uploaded && task.status === 'pending' && !isUploading;

  return (
    <div className="space-y-6">
      {/* Status Card */}
      <Card>
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <CardTitle className="flex items-center gap-2">
              <span className="text-xl">{statusInfo.icon}</span>
              <span className={cn('font-medium', statusInfo.color)}>
                {statusInfo.label}
              </span>
            </CardTitle>
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <Clock className="h-4 w-4" />
              <span>剩余时间: {timeRemaining}</span>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {/* Progress */}
          {(isBuilding || isSuccess) && progress && (
            <div className="mb-4">
              <div className="mb-2 flex items-center justify-between text-sm">
                <span className="text-muted-foreground">构建进度</span>
                <span className="font-medium">{progress.progress}%</span>
              </div>
              <Progress value={progress.progress} />
              {progress.current_step && (
                <p className="mt-2 text-sm text-muted-foreground">
                  {progress.current_step}
                </p>
              )}
            </div>
          )}

          {/* Error Message */}
          {isFailed && task.error_message && (
            <div className="mb-4 rounded-lg border border-red-200 bg-red-50 p-4">
              <div className="flex items-start gap-3">
                <AlertTriangle className="h-5 w-5 shrink-0 text-red-600" />
                <div>
                  <p className="font-medium text-red-800">构建失败</p>
                  <p className="mt-1 text-sm text-red-700">{task.error_message}</p>
                </div>
              </div>
            </div>
          )}

          {/* Task Info */}
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="rounded-lg bg-muted/30 p-3">
              <p className="text-xs text-muted-foreground">任务ID</p>
              <p className="font-mono text-sm">{task.task_id}</p>
            </div>
            <div className="rounded-lg bg-muted/30 p-3">
              <p className="text-xs text-muted-foreground">目标架构</p>
              <p className="font-medium">{task.target_arch}</p>
            </div>
            <div className="rounded-lg bg-muted/30 p-3">
              <p className="text-xs text-muted-foreground">创建时间</p>
              <p className="font-medium">{formatDateTime(task.created_at)}</p>
            </div>
            <div className="rounded-lg bg-muted/30 p-3">
              <p className="text-xs text-muted-foreground flex items-center gap-1.5">
                <FileCode className="h-3.5 w-3.5" />
                Dockerfile
                <span className="text-destructive">*</span>
              </p>
              <p className={cn(
                "font-medium mt-1",
                task.dockerfile_uploaded ? "text-green-600" : "text-yellow-600"
              )}>
                {task.dockerfile_uploaded ? "✓ 已上传" : "⏳ 等待上传..."}
              </p>
              {!task.dockerfile_uploaded && (
                <p className="text-xs text-muted-foreground mt-0.5">
                  请在上方的构建配置区域上传 Dockerfile
                </p>
              )}
            </div>
            <div className="rounded-lg bg-muted/30 p-3">
              <p className="text-xs text-muted-foreground flex items-center gap-1.5">
                <FolderArchive className="h-3.5 w-3.5" />
                构建上下文
              </p>
              <p className={cn(
                "font-medium mt-1",
                task.context_uploaded ? "text-green-600" : "text-muted-foreground"
              )}>
                {task.context_uploaded ? "✓ 已上传 (可选)" : "未上传 (可选)"}
              </p>
              {!task.context_uploaded && (
                <p className="text-xs text-muted-foreground mt-0.5">
                  如需 COPY/ADD 指令，上传上下文文件
                </p>
              )}
            </div>
          </div>

          {/* 上传状态提示 */}
          {!task.dockerfile_uploaded && task.status === 'pending' && (
            <div className="mt-4 rounded-lg border border-blue-200 bg-blue-50 p-3">
              <p className="text-sm text-blue-700">
                <strong>请先上传 Dockerfile</strong>，上传完成后再点击「开始构建」按钮。
                {!task.context_uploaded && " 上下文文件正在上传中，请稍候..."}
              </p>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Logs */}
      {(isBuilding || (progress?.logs && progress.logs.length > 0)) && (
        <BuildLogs logs={progress?.logs || []} isBuilding={isBuilding} />
      )}

      {/* Actions */}
      <div className="flex flex-wrap justify-end gap-3">
        {/* Delete */}
        <Button
          variant="outline"
          onClick={onDelete}
          disabled={isBuilding}
          className="text-destructive hover:text-destructive"
        >
          <Trash2 className="mr-2 h-4 w-4" />
          删除任务
        </Button>

        {/* Reset */}
        {(isSuccess || isFailed) && (
          <Button variant="outline" onClick={onReset}>
            <RefreshCw className="mr-2 h-4 w-4" />
            新建任务
          </Button>
        )}

        {/* Start Build */}
        {task.status === 'pending' && (
          <Button
            onClick={onStartBuild}
            disabled={isStarting || !canActuallyStartBuild}
            className={cn(
              !canActuallyStartBuild && "opacity-50"
            )}
          >
            {isStarting ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                启动中...
              </>
            ) : isUploading ? (
              <>
                ⏳ 文件上传中...
              </>
            ) : !task.dockerfile_uploaded ? (
              <>
                ⏳ 等待上传 Dockerfile
              </>
            ) : (
              <>
                🚀 开始构建
              </>
            )}
          </Button>
        )}

        {/* Download */}
        {isSuccess && task.download_url && (
          <Button variant="success" onClick={onDownload}>
            <Download className="mr-2 h-4 w-4" />
            下载镜像
          </Button>
        )}

        {/* Debug Button - 仅在失败时显示 */}
        {isFailed && (
          <Button
            variant="ghost"
            size="sm"
            onClick={toggleDebug}
            disabled={debugLoading}
            className="text-muted-foreground"
          >
            {debugLoading ? (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            ) : showDebug ? (
              <ChevronUp className="mr-2 h-4 w-4" />
            ) : (
              <Bug className="mr-2 h-4 w-4" />
            )}
            调试信息
          </Button>
        )}
      </div>

      {/* Debug Info Panel */}
      {showDebug && (
        <Card className="border-dashed border-2 border-orange-300 bg-orange-50/50">
          <CardHeader className="py-2">
            <CardTitle className="text-sm flex items-center gap-2 text-orange-700">
              <Bug className="h-4 w-4" />
              存储调试信息
              <Button
                variant="ghost"
                size="sm"
                onClick={loadStorageDebug}
                disabled={debugLoading}
                className="ml-auto h-6 text-xs"
              >
                <RefreshCw className={cn("h-3 w-3", debugLoading && "animate-spin")} />
              </Button>
            </CardTitle>
          </CardHeader>
          <CardContent className="text-xs font-mono">
            {storageInfo ? (
              <div className="space-y-2">
                <div>
                  <strong>存储类型:</strong> {storageInfo.info?.storage_type}
                </div>
                <div>
                  <strong>存储配置:</strong> {storageInfo.info?.is_configured ? '已配置' : '未配置'}
                </div>
                <div>
                  <strong>当前任务相关文件:</strong>
                  <pre className="mt-1 p-2 bg-white rounded border overflow-auto max-h-32">
                    {JSON.stringify(storageInfo.files, null, 2)}
                  </pre>
                </div>
                <div>
                  <strong>预期 Dockerfile 路径:</strong> uploads/{task.task_id}/Dockerfile
                </div>
                <div>
                  <strong>预期上下文路径:</strong> uploads/{task.task_id}/context/
                </div>
              </div>
            ) : (
              <p className="text-muted-foreground">加载中...</p>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
