import {
  Avatar,
  AvatarFallback,
  AvatarImage,
} from '@/components/ui/avatar';
import { AuthenticatedImage } from '@/components/ui/authenticated-image';
import { cn } from '@/lib/utils';
import type { UIMessage } from 'ai';
import type { ComponentProps, HTMLAttributes } from 'react';
import { useUploadBlobUrl } from '@/services/uploads/uploads.hooks';

export type MessageProps = HTMLAttributes<HTMLDivElement> & {
  from: UIMessage['role'];
};

export const Message = ({ className, from, ...props }: MessageProps) => (
  <div
    className={cn(
      'group flex w-full gap-2 py-4',
      // Avatar en haut pour assistant, en bas pour user
      from === 'user' ? 'is-user justify-end items-end' : 'is-assistant justify-start items-start',
      // Largeur max réduite pour messages user (45ch au lieu de 65ch)
      from === 'user' ? '[&>div]:max-w-[45ch]' : '[&>div]:max-w-full',
      className
    )}
    {...props}
  />
);

export type MessageContentProps = HTMLAttributes<HTMLDivElement>;

export const MessageContent = ({
  children,
  className,
  ...props
}: MessageContentProps) => (
  <div
    className={cn(
      // Texte plus grand (text-base au lieu de text-sm)
      'flex flex-col gap-2 overflow-hidden rounded-lg px-4 py-3 text-foreground text-base',
      // Messages user : avec bulle
      'group-[.is-user]:bg-primary group-[.is-user]:text-primary-foreground',
      // Messages assistant : sans bulle visible (transparent) + padding horizontal pour respirer
      'group-[.is-assistant]:bg-transparent group-[.is-assistant]:text-foreground group-[.is-assistant]:px-2 group-[.is-assistant]:py-2',
      className
    )}
    {...props}
  >
    <div className="is-user:dark">{children}</div>
  </div>
);

export type MessageAvatarProps = ComponentProps<typeof Avatar> & {
  src?: string; // Deprecated: use uploadId instead
  uploadId?: string | null; // Upload ID for authenticated images
  fallback?: string; // Fallback public URL if uploadId is not provided
  name?: string;
};

export const MessageAvatar = ({
  src, // Legacy support
  uploadId,
  fallback,
  name,
  className,
  ...props
}: MessageAvatarProps) => {
  // Fetch authenticated blob URL if uploadId provided
  const { data: blobUrl } = useUploadBlobUrl(uploadId);

  // Determine final src: blobUrl > src (legacy) > fallback
  const finalSrc = blobUrl || src || fallback;

  return (
    <Avatar
      className={cn('size-8 ring ring-1 ring-border shrink-0 mt-1', className)}
      {...props}
    >
      {finalSrc && <AvatarImage alt="" className="mt-0 mb-0" src={finalSrc} />}
      <AvatarFallback>{name?.slice(0, 2) || ''}</AvatarFallback>
    </Avatar>
  );
};
