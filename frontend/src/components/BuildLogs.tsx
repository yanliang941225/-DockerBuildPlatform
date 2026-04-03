import { useEffect, useRef } from 'react';
import { cn } from '@/lib/utils';
import type { LogEntry } from '@/types';

interface BuildLogsProps {
  logs: LogEntry[];
  isBuilding?: boolean;
}

export function BuildLogs({ logs, isBuilding = false }: BuildLogsProps) {
  const logsEndRef = useRef<HTMLDivElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    logsEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [logs]);

  const getLogColor = (level: string) => {
    switch (level) {
      case 'error':
        return 'text-red-600 bg-red-50';
      case 'warning':
        return 'text-yellow-600 bg-yellow-50';
      case 'success':
        return 'text-green-600 bg-green-50';
      default:
        return 'text-muted-foreground';
    }
  };

  const getLogPrefix = (level: string) => {
    switch (level) {
      case 'error':
        return '❌';
      case 'warning':
        return '⚠️';
      case 'success':
        return '✅';
      default:
        return '📝';
    }
  };

  const formatTimestamp = (timestamp: string) => {
    const date = new Date(timestamp);
    return date.toLocaleTimeString('zh-CN', {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    });
  };

  if (logs.length === 0) {
    return (
      <div className="flex h-64 flex-col items-center justify-center rounded-lg border bg-muted/20 p-8 text-center">
        <p className="text-lg font-medium text-muted-foreground">暂无构建日志</p>
        <p className="mt-1 text-sm text-muted-foreground/70">
          开始构建后将显示实时日志
        </p>
      </div>
    );
  }

  return (
    <div className="rounded-xl border bg-card">
      <div className="flex items-center justify-between border-b px-4 py-3">
        <div className="flex items-center gap-2">
          <h3 className="font-medium">构建日志</h3>
          {isBuilding && (
            <span className="relative flex h-2 w-2">
              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-primary opacity-75"></span>
              <span className="relative inline-flex h-2 w-2 rounded-full bg-primary"></span>
            </span>
          )}
        </div>
        <span className="text-sm text-muted-foreground">{logs.length} 条</span>
      </div>

      <div 
        ref={containerRef}
        className="h-80 overflow-y-auto p-4"
        style={{ scrollBehavior: 'smooth' }}
      >
        <div className="space-y-1 font-mono text-sm">
          {logs.map((log, index) => (
            <div
              key={index}
              className={cn(
                'flex items-start gap-2 rounded px-2 py-1',
                getLogColor(log.level)
              )}
            >
              <span className="shrink-0 opacity-70">
                {getLogPrefix(log.level)}
              </span>
              <span className="shrink-0 text-xs opacity-50">
                {formatTimestamp(log.timestamp)}
              </span>
              <span className="break-all">{log.message}</span>
            </div>
          ))}
          <div ref={logsEndRef} />
        </div>
      </div>
    </div>
  );
}
