import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Download, FileText, Paperclip } from "lucide-react";
import { useRef, useState } from "react";
import { useTranslation } from "react-i18next";

import { Button } from "@/components/ui/Button";
import { Card, CardBody } from "@/components/ui/Card";
import { Label, Textarea } from "@/components/ui/Input";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { EmptyState, ErrorState, LoadingState } from "@/components/ui/States";
import { getErrorMessage } from "@/services/api";
import { explanationLettersApi } from "@/services/explanationLettersApi";
import type { ExplanationLetterResponse } from "@/types/models";
import { formatDateShort } from "@/utils/format";
import { letterStatusTokens } from "@/utils/status";

export function EmployeeExplanationLettersPage() {
  const { t } = useTranslation();
  const lettersQuery = useQuery({
    queryKey: ["explanation-letters", "me"],
    queryFn: () => explanationLettersApi.list({ page_size: 50 }),
  });

  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-display text-2xl font-semibold text-ink">{t("letters.title")}</h1>
        <p className="text-sm text-ink-muted">{t("letters.employeeSubtitle")}</p>
      </div>

      {lettersQuery.isLoading && <LoadingState label={t("common.loading")} />}
      {lettersQuery.isError && <ErrorState message={t("letters.couldNotLoad")} />}

      {lettersQuery.data &&
        (lettersQuery.data.items.length === 0 ? (
          <EmptyState title={t("letters.noLetters")} icon={<FileText size={28} />} description={t("letters.noLettersEmployeeDescription")} />
        ) : (
          <div className="space-y-4">
            {lettersQuery.data.items.map((letter) => (
              <LetterCard key={letter.id} letter={letter} />
            ))}
          </div>
        ))}
    </div>
  );
}

function LetterCard({ letter: initial }: { letter: ExplanationLetterResponse }) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const [letter, setLetter] = useState(initial);
  const [text, setText] = useState(letter.employee_explanation ?? "");
  const [error, setError] = useState<string | null>(null);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Editable up until HR has actually reviewed it - an employee can revise their
  // explanation (text or file) after first submitting, as long as no decision
  // has been made yet.
  const canEdit = letter.status !== "reviewed";
  const hasSubmittedBefore = letter.employee_explanation !== null;

  const submitMutation = useMutation({
    mutationFn: () => explanationLettersApi.submitExplanation(letter.id, text.trim()),
    onSuccess: (updated) => {
      setLetter(updated);
      void queryClient.invalidateQueries({ queryKey: ["notifications"] });
    },
    onError: (err: unknown) => setError(getErrorMessage(err)),
  });

  const uploadMutation = useMutation({
    mutationFn: (file: File) => explanationLettersApi.uploadAttachment(letter.id, file),
    onSuccess: (updated) => {
      setLetter(updated);
      void queryClient.invalidateQueries({ queryKey: ["notifications"] });
    },
    onError: (err: unknown) => setUploadError(getErrorMessage(err)),
  });

  async function downloadPdf() {
    await explanationLettersApi.downloadPdf(letter.id, letter.employee.employee_id, letter.date);
  }

  async function downloadAttachment() {
    await explanationLettersApi.downloadAttachment(letter.id, `explanation-${letter.employee.employee_id}-${letter.date}`);
  }

  function onFileSelected(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) return;
    setUploadError(null);
    uploadMutation.mutate(file);
    event.target.value = "";
  }

  return (
    <Card>
      <CardBody className="space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div>
            <p className="font-medium text-ink">
              {t("letters.arrivedLate", { minutes: letter.late_minutes, date: formatDateShort(letter.date) })}
            </p>
          </div>
          <StatusBadge tokens={letterStatusTokens(letter.status)} />
        </div>

        {canEdit ? (
          <div className="space-y-3">
            <div>
              <Label htmlFor={`explanation-${letter.id}`}>{t("letters.writeExplanation")}</Label>
              <Textarea
                id={`explanation-${letter.id}`}
                rows={3}
                value={text}
                onChange={(event) => setText(event.target.value)}
                placeholder={t("letters.explanationPlaceholder") ?? undefined}
              />
              {error && <p className="mt-1 text-sm text-status-danger">{error}</p>}
              <div className="mt-2 flex items-center gap-3">
                <Button
                  size="sm"
                  onClick={() => {
                    setError(null);
                    submitMutation.mutate();
                  }}
                  disabled={!text.trim() || submitMutation.isPending}
                >
                  {submitMutation.isPending ? t("common.saving") : hasSubmittedBefore ? t("letters.update") : t("letters.submit")}
                </Button>
                <button
                  type="button"
                  onClick={() => void downloadPdf()}
                  className="flex items-center gap-1 text-sm font-medium text-brand hover:text-brand-hover"
                >
                  <Download size={14} /> {t("letters.download")}
                </button>
              </div>
            </div>

            <div className="border-t border-line pt-3">
              <Label>{t("letters.uploadFile")}</Label>
              <p className="mb-2 text-xs text-ink-muted">{t("letters.uploadFileHint")}</p>
              <div className="flex flex-wrap items-center gap-3">
                <input
                  ref={fileInputRef}
                  type="file"
                  accept="application/pdf,image/jpeg,image/png,image/webp"
                  onChange={onFileSelected}
                  className="block text-sm text-ink-muted"
                  disabled={uploadMutation.isPending}
                />
                {uploadMutation.isPending && <span className="text-xs text-ink-muted">{t("letters.uploading")}</span>}
                {letter.attachment_url && (
                  <button
                    type="button"
                    onClick={() => void downloadAttachment()}
                    className="flex items-center gap-1 text-sm font-medium text-brand hover:text-brand-hover"
                  >
                    <Paperclip size={14} /> {t("letters.viewAttachment")}
                  </button>
                )}
              </div>
              {uploadError && <p className="mt-1 text-sm text-status-danger">{uploadError}</p>}
            </div>
          </div>
        ) : (
          <div className="space-y-3">
            <div>
              <Label>{t("letters.employeeExplanation")}</Label>
              <p className="rounded-lg border border-line bg-canvas px-3 py-2 text-sm text-ink">{letter.employee_explanation}</p>
            </div>
            {letter.hr_comment && (
              <div>
                <Label>{t("letters.hrComment")}</Label>
                <p className="rounded-lg border border-line bg-canvas px-3 py-2 text-sm text-ink">{letter.hr_comment}</p>
              </div>
            )}
            <div className="flex flex-wrap items-center gap-3">
              <button
                type="button"
                onClick={() => void downloadPdf()}
                className="flex items-center gap-1 text-sm font-medium text-brand hover:text-brand-hover"
              >
                <Download size={14} /> {t("letters.download")}
              </button>
              {letter.attachment_url && (
                <button
                  type="button"
                  onClick={() => void downloadAttachment()}
                  className="flex items-center gap-1 text-sm font-medium text-brand hover:text-brand-hover"
                >
                  <Paperclip size={14} /> {t("letters.viewAttachment")}
                </button>
              )}
            </div>
          </div>
        )}
      </CardBody>
    </Card>
  );
}
