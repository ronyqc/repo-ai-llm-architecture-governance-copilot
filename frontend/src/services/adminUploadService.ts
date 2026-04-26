import { apiPost } from "./api";
import type {
  IngestRequest,
  IngestResponse,
  UploadUrlRequest,
  UploadUrlResponse,
} from "../types/adminUpload";

export async function requestUploadUrl(
  payload: UploadUrlRequest,
  accessToken: string
): Promise<UploadUrlResponse> {
  return apiPost<UploadUrlResponse>("/api/v1/upload-url", payload, accessToken);
}

export async function uploadFileToBlob(
  uploadUrl: string,
  file: File
): Promise<void> {
  const response = await fetch(uploadUrl, {
    method: "PUT",
    headers: {
      "x-ms-blob-type": "BlockBlob",
      "Content-Type": file.type || "application/octet-stream",
    },
    body: file,
  });

  if (!response.ok) {
    throw new Error(
      `La subida a Blob Storage fallo con estado ${response.status}.`
    );
  }
}

export async function requestDocumentIngest(
  payload: IngestRequest,
  accessToken: string
): Promise<IngestResponse> {
  return apiPost<IngestResponse>("/api/v1/ingest", payload, accessToken);
}
