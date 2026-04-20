import { useId, useState, type ChangeEvent } from "react";
import { useAuth } from "../auth/useAuth";
import {
  requestDocumentIngest,
  requestUploadUrl,
  uploadFileToBlob,
} from "../services/adminUploadService";
import type {
  AdminUploadPhase,
  IngestResponse,
  KnowledgeDomain,
  UploadUrlResponse,
} from "../types/adminUpload";

const KNOWLEDGE_DOMAINS: Array<{
  value: KnowledgeDomain;
  label: string;
}> = [
  { value: "bian", label: "bian" },
  { value: "building_blocks", label: "building_blocks" },
  { value: "guidelines_patterns", label: "guidelines_patterns" },
];

function getPhaseMessage(
  phase: AdminUploadPhase,
  uploadData: UploadUrlResponse | null,
  ingestData: IngestResponse | null
): string {
  switch (phase) {
    case "subiendo":
      return "Subiendo archivo a raw-corpus...";
    case "subido":
      return uploadData
        ? `Archivo subido a raw-corpus como ${uploadData.blob_name}.`
        : "Archivo subido correctamente.";
    case "procesando":
      return "Solicitando procesamiento documental...";
    case "procesado":
      return ingestData
        ? `Documento enviado al pipeline. Trace ID: ${ingestData.trace_id}.`
        : "Documento procesado correctamente.";
    case "error":
      return "Ocurrio un error durante la operacion administrativa.";
    default:
      return "Selecciona un archivo, subelo a raw-corpus y luego solicita el procesamiento.";
  }
}

export function AdminUploadPanel() {
  const { accessToken, refreshAccessToken, isAuthenticated, isAdmin, account } =
    useAuth();
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [knowledgeDomain, setKnowledgeDomain] =
    useState<KnowledgeDomain>("bian");
  const [phase, setPhase] = useState<AdminUploadPhase>("idle");
  const [panelError, setPanelError] = useState<string | null>(null);
  const [uploadData, setUploadData] = useState<UploadUrlResponse | null>(null);
  const [ingestData, setIngestData] = useState<IngestResponse | null>(null);
  const fileInputId = useId();

  if (!isAdmin) {
    return null;
  }

  const isUploading = phase === "subiendo";
  const isProcessing = phase === "procesando";
  const hasUploadedFile = uploadData !== null;
  const canUpload =
    Boolean(selectedFile) && isAuthenticated && !isUploading && !isProcessing;
  const canProcess =
    hasUploadedFile && isAuthenticated && !isUploading && !isProcessing;

  const resolveAccessToken = async (): Promise<string> => {
    const tokenToUse = accessToken ?? (await refreshAccessToken());
    if (!tokenToUse) {
      throw new Error(
        "No se pudo obtener el token de acceso para la operacion administrativa."
      );
    }
    return tokenToUse;
  };

  const handleFileChange = (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0] ?? null;
    setSelectedFile(file);
    setUploadData(null);
    setIngestData(null);
    setPanelError(null);
    setPhase("idle");
  };

  const handleUpload = async () => {
    if (!selectedFile) {
      setPanelError("Debes seleccionar un archivo antes de subirlo.");
      return;
    }

    try {
      setPanelError(null);
      setIngestData(null);
      setPhase("subiendo");

      const tokenToUse = await resolveAccessToken();
      const uploadUrlResult = await requestUploadUrl(
        { file_name: selectedFile.name },
        tokenToUse
      );
      await uploadFileToBlob(uploadUrlResult.upload_url, selectedFile);

      setUploadData(uploadUrlResult);
      setPhase("subido");
    } catch (error) {
      setPanelError(
        error instanceof Error
          ? error.message
          : "No se pudo subir el archivo a raw-corpus."
      );
      setPhase("error");
    }
  };

  const handleProcess = async () => {
    if (!selectedFile || !uploadData) {
      setPanelError("Primero debes subir el archivo a raw-corpus.");
      return;
    }

    try {
      setPanelError(null);
      setPhase("procesando");

      const tokenToUse = await resolveAccessToken();
      const ingestResult = await requestDocumentIngest(
        {
          file_name: selectedFile.name,
          file_url: uploadData.blob_url,
          knowledge_domain: knowledgeDomain,
          metadata: {
            source_system: "frontend_admin_panel",
            uploaded_by: account?.username ?? "admin_user",
          },
        },
        tokenToUse
      );

      setIngestData(ingestResult);
      setPhase("procesado");
    } catch (error) {
      setPanelError(
        error instanceof Error
          ? error.message
          : "No se pudo enviar el documento al pipeline."
      );
      setPhase("error");
    }
  };

  return (
    <section className="panel admin-panel">
      <div className="panel-title-row">
        <div>
          <h2>Panel Admin</h2>
          <p className="panel-subtitle">
            Carga documentos a raw-corpus y luego dispara la ingesta administrativa.
          </p>
        </div>
        <span className="admin-badge">Admin</span>
      </div>

      <div className="admin-grid">
        <div className="field-group">
          <label htmlFor={fileInputId}>Archivo</label>
          <input
            id={fileInputId}
            type="file"
            onChange={handleFileChange}
            disabled={isUploading || isProcessing}
          />
          <small className="field-help">
            Formatos permitidos: md, txt, html, htm, pdf, docx.
          </small>
        </div>

        <div className="field-group">
          <label htmlFor="knowledge-domain">Knowledge domain</label>
          <select
            id="knowledge-domain"
            value={knowledgeDomain}
            onChange={(event) =>
              setKnowledgeDomain(event.target.value as KnowledgeDomain)
            }
            disabled={isUploading || isProcessing}
          >
            {KNOWLEDGE_DOMAINS.map((domain) => (
              <option key={domain.value} value={domain.value}>
                {domain.label}
              </option>
            ))}
          </select>
        </div>
      </div>

      <div className="admin-actions">
        <button disabled={!canUpload} onClick={() => void handleUpload()}>
          {isUploading ? "Subiendo..." : "Subir a raw-corpus"}
        </button>
        <button
          className="secondary-button"
          disabled={!canProcess}
          onClick={() => void handleProcess()}
        >
          {isProcessing ? "Procesando..." : "Procesar documento"}
        </button>
      </div>

      <div className="status-card">
        <strong>Estado:</strong> {getPhaseMessage(phase, uploadData, ingestData)}
      </div>

      {selectedFile && (
        <div className="status-meta">
          <span>Archivo: {selectedFile.name}</span>
          <span>Domain: {knowledgeDomain}</span>
        </div>
      )}

      {uploadData && (
        <div className="status-meta">
          <span>Blob: {uploadData.blob_name}</span>
          <span>Expira en: {uploadData.expires_in_seconds} s</span>
        </div>
      )}

      {ingestData && (
        <div className="status-meta">
          <span>Estado ingest: {ingestData.status}</span>
          <span>Trace: {ingestData.trace_id}</span>
        </div>
      )}

      {panelError && <div className="error-banner">{panelError}</div>}
    </section>
  );
}
