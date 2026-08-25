import { useRef, useState } from "react";
import type { DragEvent } from "react";

interface DropzoneProps {
  label: string;
  hint?: string;
  accept?: string;
  multiple?: boolean;
  onFiles: (files: File[]) => void;
}

export default function Dropzone({ label, hint, accept, multiple, onFiles }: DropzoneProps) {
  const [isDragging, setIsDragging] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleDrop = (event: DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    setIsDragging(false);
    const files = Array.from(event.dataTransfer.files);
    if (files.length > 0) onFiles(multiple ? files : [files[0]]);
  };

  return (
    <div
      onDragOver={(e) => {
        e.preventDefault();
        setIsDragging(true);
      }}
      onDragLeave={() => setIsDragging(false)}
      onDrop={handleDrop}
      onClick={() => inputRef.current?.click()}
      role="button"
      tabIndex={0}
      className={`cursor-pointer rounded-lg border-2 border-dashed p-8 text-center transition-colors ${
        isDragging
          ? "border-indigo-400 bg-indigo-500/10"
          : "border-slate-700 hover:border-slate-600"
      }`}
    >
      <input
        ref={inputRef}
        type="file"
        accept={accept}
        multiple={multiple}
        className="hidden"
        onChange={(e) => {
          const files = e.target.files ? Array.from(e.target.files) : [];
          if (files.length > 0) onFiles(files);
          e.target.value = "";
        }}
      />
      <p className="text-sm font-medium text-slate-200">{label}</p>
      <p className="mt-1 text-xs text-slate-500">
        {hint ?? "Drag and drop, or click to browse"}
      </p>
    </div>
  );
}
