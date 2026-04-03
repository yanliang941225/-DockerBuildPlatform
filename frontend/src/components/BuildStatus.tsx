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
  AlertTriangle
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { formatTimeRemaining, formatDateTime } from '@/lib/utils';
import { STATUS_INFO } from '@/types';
import type { Task, BuildProgress } from '@/types';

interface BuildStatusProps {
  task: Task;
  progress: BuildProgress | null;
  onStartBuild: () => void;
  onDownload: () => void;
  onDelete: () => void;
  onReset: () => void;
  canStartBuild: boolean;
  isStarting: boolean;
}

export function BuildStatus({
  task,
  progress,
  onStartBuild,
  onDownload,
  onDelete,
  onReset,
  canStartBuild,
  isStarting,
}: BuildStatusProps) {
  const statusInfo = STATUS_INFO[task.status];
  const isBuilding = task.status === 'building' || task.status === 'uploading';
  const isSuccess = task.status === 'success';
  const isFailed = task.status === 'failed';
  const timeRemaining = formatTimeRemaining(task.expires_at);

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
              <p className="text-xs text-muted-foreground">目标架构</p>
              <p className="font-medium">{task.target_arch}</p>
            </div>
            <div className="rounded-lg bg-muted/30 p-3">
              <p className="text-xs text-muted-foreground">创建时间</p>
              <p className="font-medium">{formatDateTime(task.created_at)}</p>
            </div>
            <div className="rounded-lg bg-muted/30 p-3">
              <p className="text-xs text-muted-foreground">Dockerfile</p>
              <p className={cn(
                "font-medium",
                task.dockerfile_uploaded ? "text-green-600" : "text-yellow-600"
              )}>
                {task.dockerfile_uploaded ? "已上传 ✓" : "未上传"}
              </p>
            </div>
            <div className="rounded-lg bg-muted/30 p-3">
              <p className="text-xs text-muted-foreground">构建上下文</p>
              <p className={cn(
                "font-medium",
                task.context_uploaded ? "text-green-600" : "text-muted-foreground"
              )}>
                {task.context_uploaded ? "已上传 ✓" : "未上传 (可选)"}
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Logs */}
      {(isBuilding || progress?.logs.length) && (
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
        {canStartBuild && (
          <Button onClick={onStartBuild} disabled={isStarting}>
            {isStarting ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                启动中...
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
      </div>
    </div>
  );
}
