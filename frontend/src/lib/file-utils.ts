import {
  FileTextIcon,
  FileArchiveIcon,
  FileSpreadsheetIcon,
  VideoIcon,
  HeadphonesIcon,
  ImageIcon,
  FileIcon,
} from "lucide-react"

/**
 * Retourne l'icône Lucide appropriée selon le type MIME et le nom du fichier
 */
export function getFileIcon(fileType: string, fileName?: string) {
  // Documents PDF et Word
  if (
    fileType.includes("pdf") ||
    fileName?.endsWith(".pdf") ||
    fileType.includes("word") ||
    fileType.includes("document") ||
    fileName?.endsWith(".doc") ||
    fileName?.endsWith(".docx")
  ) {
    return FileTextIcon
  }

  // Archives
  if (
    fileType.includes("zip") ||
    fileType.includes("archive") ||
    fileType.includes("compressed") ||
    fileName?.endsWith(".zip") ||
    fileName?.endsWith(".rar") ||
    fileName?.endsWith(".7z")
  ) {
    return FileArchiveIcon
  }

  // Tableurs Excel
  if (
    fileType.includes("excel") ||
    fileType.includes("spreadsheet") ||
    fileName?.endsWith(".xls") ||
    fileName?.endsWith(".xlsx")
  ) {
    return FileSpreadsheetIcon
  }

  // Vidéos
  if (fileType.includes("video/")) {
    return VideoIcon
  }

  // Audio
  if (fileType.includes("audio/")) {
    return HeadphonesIcon
  }

  // Images
  if (fileType.startsWith("image/")) {
    return ImageIcon
  }

  // Fichier générique
  return FileIcon
}

/**
 * Retourne un label court pour le badge selon le type MIME ou l'extension
 */
export function getFileTypeBadge(fileType: string, fileName?: string): string {
  // PDF
  if (fileType.includes("pdf") || fileName?.endsWith(".pdf")) {
    return "PDF"
  }

  // Word
  if (
    fileType.includes("word") ||
    fileType.includes("document") ||
    fileName?.endsWith(".doc") ||
    fileName?.endsWith(".docx")
  ) {
    return "DOC"
  }

  // Excel
  if (
    fileType.includes("excel") ||
    fileType.includes("spreadsheet") ||
    fileName?.endsWith(".xls") ||
    fileName?.endsWith(".xlsx")
  ) {
    return "XLS"
  }

  // Archives
  if (
    fileType.includes("zip") ||
    fileType.includes("archive") ||
    fileName?.endsWith(".zip")
  ) {
    return "ZIP"
  }

  if (fileName?.endsWith(".rar")) {
    return "RAR"
  }

  // Images
  if (fileType === "image/png" || fileName?.endsWith(".png")) {
    return "PNG"
  }

  if (
    fileType === "image/jpeg" ||
    fileName?.endsWith(".jpg") ||
    fileName?.endsWith(".jpeg")
  ) {
    return "JPG"
  }

  if (fileType === "image/gif" || fileName?.endsWith(".gif")) {
    return "GIF"
  }

  if (fileType === "image/webp" || fileName?.endsWith(".webp")) {
    return "WEBP"
  }

  if (fileType === "image/svg+xml" || fileName?.endsWith(".svg")) {
    return "SVG"
  }

  // Texte
  if (fileType.includes("text/plain") || fileName?.endsWith(".txt")) {
    return "TXT"
  }

  // Vidéo
  if (fileType.startsWith("video/")) {
    return "VIDEO"
  }

  // Audio
  if (fileType.startsWith("audio/")) {
    return "AUDIO"
  }

  // Par défaut, extraire l'extension du fichier
  if (fileName) {
    const extension = fileName.split(".").pop()?.toUpperCase()
    if (extension && extension.length <= 4) {
      return extension
    }
  }

  return "FILE"
}
