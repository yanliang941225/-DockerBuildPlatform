import { useCallback, useState } from 'react';
import { useDropzone, type FileRejection } from 'react-dropzone';
import { Upload, File as FileIcon, X, CheckCircle, AlertCircle, Loader2, Clock } from 'lucide-react';
import { cn } from '@/lib/utils';
import { formatBytes } from '@/lib/utils';

interface FileUploaderProps {
  maxSize?: number;
  onFileSelect: (file: File) => void;
  selectedFile: File | null;
  title: string;
  description: string;
  disabled?: boolean;
  allowedExtensions?: string[];
  // 新增：上传进度
  uploadProgress?: number; // 0-100
  isUploading?: boolean;
  // 新增：是否等待创建任务（任务还未创建但文件已选择）
  isPendingTask?: boolean;
}

// 验证文件扩展名
function validateExtension(file: File, allowedExtensions: string[]): FileRejection[] {
  // 如果没有限制，接受所有文件
  if (!allowedExtensions || allowedExtensions.length === 0) return [];

  const filename = file.name.toLowerCase();

  // 检查完全匹配（如 Dockerfile）
  for (const ext of allowedExtensions) {
    const cleanExt = ext.toLowerCase();
    // 完全匹配文件名
    if (filename === cleanExt) {
      return [];
    }
    // 检查扩展名（带或不带点）
    const extWithDot = cleanExt.startsWith('.') ? cleanExt : '.' + cleanExt;
    if (filename.endsWith(extWithDot)) {
      return [];
    }
  }

  return [{
    file,
    errors: [{
      code: 'file-invalid-type',
      message: `不支持的文件类型，仅支持: ${allowedExtensions.join(', ')}`
    }]
  }];
}

export function FileUploader({
  maxSize = 500 * 1024 * 1024,
  onFileSelect,
  selectedFile,
  title,
  description,
  disabled = false,
  allowedExtensions = [],
  uploadProgress = 0,
  isUploading = false,
  isPendingTask = false,
}: FileUploaderProps) {
  const [error, setError] = useState<string | null>(null);

  const onDrop = useCallback(
    (acceptedFiles: File[], fileRejections: FileRejection[]) => {
      setError(null);

      // 自定义扩展名验证
      if (acceptedFiles.length > 0) {
        const file = acceptedFiles[0];
        const extensionErrors = validateExtension(file, allowedExtensions);
        
        if (extensionErrors.length > 0) {
          setError(extensionErrors[0].errors[0]?.message || '文件验证失败');
          return;
        }
        
        onFileSelect(file);
      }
      
      // 处理浏览器拒绝的文件
      if (fileRejections.length > 0) {
        const errorMsg = fileRejections[0].errors[0]?.message || '文件验证失败';
        setError(errorMsg);
      }
    },
    [onFileSelect, allowedExtensions]
  );

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    maxSize,
    multiple: false,
    disabled,
    // 不设置 accept，让浏览器接受所有文件，由我们自定义验证
  });

  const handleRemove = (e: React.MouseEvent) => {
    e.stopPropagation();
    // 传递 null 来清除文件
    onFileSelect(null as unknown as File);
    setError(null);
  };

  // 判断是否正在上传中（文件已选择但上传未完成）
  // selectedFile 必须是有效的 File 对象
  const isInUploadState = selectedFile instanceof File && isUploading;
  const isUploadComplete = selectedFile instanceof File && !isUploading && uploadProgress === 100;
  // 判断是否等待创建任务（文件已选择但任务还未创建）
  const isPendingTaskState = selectedFile instanceof File && isPendingTask && uploadProgress === 0;

  return (
    <div
      {...getRootProps()}
      className={cn(
        'relative min-h-[120px] cursor-pointer rounded-xl border-2 border-dashed transition-all duration-200',
        isDragActive
          ? 'border-primary bg-primary/5 scale-[1.01]'
          : 'border-border hover:border-primary/50 hover:bg-muted/30',
        disabled && 'opacity-50 cursor-not-allowed',
        isUploadComplete ? 'border-green-500 bg-green-50/50' : '',
        error ? 'border-red-500 bg-red-50/50' : '',
        isInUploadState ? 'border-primary bg-primary/5' : '',
        isPendingTaskState ? 'border-amber-400 bg-amber-50/30' : ''
      )}
    >
      <input {...getInputProps()} />

      {/* 上传中状态 */}
      {isInUploadState && (
        <div className="flex flex-col items-center justify-center p-6 gap-4">
          <Loader2 className="h-10 w-10 animate-spin text-primary" />
          <div className="text-center">
            <p className="font-medium text-foreground mb-2">正在上传...</p>
            <p className="text-sm text-muted-foreground mb-3">
              {selectedFile.name} ({formatBytes(selectedFile.size)})
            </p>
            {/* 进度条 */}
            <div className="w-full max-w-xs mx-auto">
              <div className="h-2 bg-muted rounded-full overflow-hidden">
                <div
                  className="h-full bg-primary transition-all duration-300 ease-out"
                  style={{ width: `${uploadProgress}%` }}
                />
              </div>
              <p className="text-xs text-center mt-1 text-muted-foreground">
                {uploadProgress}%
              </p>
            </div>
          </div>
        </div>
      )}

      {/* 上传完成状态 */}
      {isUploadComplete && (
        <div className="flex items-center justify-between p-6">
          <div className="flex items-center gap-4">
            <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-green-100 text-green-600">
              <CheckCircle className="h-6 w-6" />
            </div>
            <div>
              <p className="font-medium text-foreground">{selectedFile.name}</p>
              <p className="text-sm text-muted-foreground">
                {formatBytes(selectedFile.size)} - 上传完成
              </p>
            </div>
          </div>
          {!disabled && (
            <button
              onClick={handleRemove}
              className="rounded-lg p-2 text-muted-foreground hover:bg-muted hover:text-foreground transition-colors"
            >
              <X className="h-5 w-5" />
            </button>
          )}
        </div>
      )}

      {/* 等待创建任务状态（文件已选择但任务还未创建） */}
      {isPendingTaskState && (
        <div className="flex items-center justify-between p-6">
          <div className="flex items-center gap-4">
            <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-amber-100 text-amber-600">
              <Clock className="h-6 w-6" />
            </div>
            <div>
              <p className="font-medium text-foreground">{selectedFile.name}</p>
              <p className="text-sm text-amber-600">
                {formatBytes(selectedFile.size)} - 等待创建任务后上传
              </p>
            </div>
          </div>
          {!disabled && (
            <button
              onClick={handleRemove}
              className="rounded-lg p-2 text-muted-foreground hover:bg-muted hover:text-foreground transition-colors"
            >
              <X className="h-5 w-5" />
            </button>
          )}
        </div>
      )}

      {/* 错误状态 */}
      {error && !isInUploadState && (
        <div className="p-6">
          <div className="flex items-center gap-4">
            <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-red-100 text-red-600">
              <AlertCircle className="h-6 w-6" />
            </div>
            <div>
              <p className="font-medium text-red-600">上传失败</p>
              <p className="text-sm text-muted-foreground">{error}</p>
            </div>
          </div>
        </div>
      )}

      {/* 默认上传区域 */}
      {!selectedFile && !error && (
        <div className="flex flex-col items-center justify-center p-8 text-center">
          <div
            className={cn(
              'mb-4 flex h-14 w-14 items-center justify-center rounded-full bg-primary/10 text-primary transition-colors',
              isDragActive && 'bg-primary/20 scale-110'
            )}
          >
            {isDragActive ? (
              <FileIcon className="h-7 w-7" />
            ) : (
              <Upload className="h-7 w-7" />
            )}
          </div>
          <p className="mb-1 font-medium text-foreground">{title}</p>
          <p className="text-sm text-muted-foreground">{description}</p>
          <p className="mt-2 text-xs text-muted-foreground/70">
            最大 {formatBytes(maxSize)}
          </p>
        </div>
      )}
    </div>
  );
}
