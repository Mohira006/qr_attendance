import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Download, FileText, Paperclip } from "lucide-react";
import { useState } from "react";
import { useTranslation } from "react-i18next";

import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Label, Select, Textarea } from "@/components/ui/Input";
import { Modal } from "@/components/ui/Modal";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { EmptyState, ErrorState, LoadingState } from "@/components/ui/States";
import { getErrorMessage } from "@/services/api";
import { explanationLettersApi } from "@/services/explanationLettersApi";
import type { LetterStatus } from "@/types/enums";
import type { ExplanationLetterResponse } from "@/types/models";
import { formatDateShort } from "@/utils/format";
import { letterStatusTokens } from "@/utils/status";

export function ExplanationLettersPage() {
  const { t } = useTranslation();
  const [status, setStatus] = useState<LetterStatus | "">("");
  const [page, setPage] = useState(1);
  const [reviewing, setReviewing] = useState<ExplanationLetterResponse | null>(null);

  const lettersQuery = useQuery({
    queryKey: ["explanation-letters", status, page],
    queryFn: () => explanationLettersApi.list({ status: status || undefined, page, page_size: 20 }),
  });

  const data = lettersQuery.data;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-display text-2xl font-semibold text-ink">{t("letters.title")}</h1>
        <p className="text-sm text-ink-muted">{t("letters.subtitle")}</p>
      </div>

      <Select
        value={status}
        onChange={(event) => {
          setStatus(event.target.value as LetterStatus | "");
          setPage(1);
        }}
        className="w-48"
      >
        <option value="">{t("common.allStatuses")}</option>
        <option value="pending">{t("common.status.pending")}</option>
        <option value="submitted">{t("common.status.submitted")}</option>
        <option value="reviewed">{t("common.status.reviewed")}</option>
      </Select>

      {lettersQuery.isLoading && <LoadingState label={t("common.loading")} />}
      {lettersQuery.isError && <ErrorState message={t("letters.couldNotLoad")} />}

      {data &&
        (data.items.length === 0 ? (
          <EmptyState title={t("letters.noLetters")} icon={<FileText size={28} />} description={t("letters.noLettersDescription")} />
        ) : (
          <Card>
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead>
                  <tr className="border-b border-line text-xs uppercase tracking-wide text-ink-muted">
                    <th className="px-4 py-3 font-medium">{t("letters.columns.employee")}</th>
                    <th className="px-4 py-3 font-medium">{t("letters.columns.date")}</th>
                    <th className="px-4 py-3 font-medium">{t("letters.columns.late")}</th>
                    <th className="px-4 py-3 font-medium">{t("attendance.columns.status")}</th>
                    <th className="px-4 py-3 font-medium" />
                  </tr>
                </thead>
                <tbody>
                  {data.items.map((letter) => (
                    <LetterRow key={letter.id} letter={letter} onReview={() => setReviewing(letter)} />
                  ))}
                </tbody>
              </table>
            </div>
            {data.pages > 1 && (
              <div className="flex items-center justify-between border-t border-line px-4 py-3">
                <p className="text-sm text-ink-muted">{t("common.page", { page: data.page, pages: data.pages })}</p>
                <div className="flex gap-2">
                  <Button variant="secondary" size="sm" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>
                    {t("common.previous")}
                  </Button>
                  <Button variant="secondary" size="sm" disabled={page >= data.pages} onClick={() => setPage((p) => p + 1)}>
                    {t("common.next")}
                  </Button>
                </div>
              </div>
            )}
          </Card>
        ))}

      {reviewing && <ReviewLetterModal letter={reviewing} onClose={() => setReviewing(null)} />}
    </div>
  );
}

function LetterRow({ letter, onReview }: { letter: ExplanationLetterResponse; onReview: () => void }) {
  const { t } = useTranslation();

  async function downloadPdf() {
    await explanationLettersApi.downloadPdf(letter.id, letter.employee.employee_id, letter.date);
  }

  return (
    <tr className="border-b border-line last:border-0 hover:bg-canvas">
      <td className="px-4 py-3">
        <div className="flex items-center gap-1.5">
          <div>
            <p className="font-medium text-ink">{letter.employee.full_name}</p>
            <p className="font-mono text-xs text-ink-muted">
              {letter.employee.employee_id} - {letter.employee.department.name}
            </p>
          </div>
          {letter.attachment_url && <Paperclip size={14} className="shrink-0 text-ink-faint" aria-label={t("letters.viewAttachment") ?? undefined} />}
        </div>
      </td>
      <td className="px-4 py-3 text-ink-muted">{formatDateShort(letter.date)}</td>
      <td className="px-4 py-3 font-medium text-status-danger">{letter.late_minutes} min</td>
      <td className="px-4 py-3">
        <StatusBadge tokens={letterStatusTokens(letter.status)} />
      </td>
      <td className="px-4 py-3 text-right">
        <div className="flex justify-end gap-3">
          <button
            type="button"
            onClick={() => void downloadPdf()}
            className="flex items-center gap-1 text-sm font-medium text-brand hover:text-brand-hover"
          >
            <Download size={14} /> {t("letters.download")}
          </button>
          <button type="button" onClick={onReview} className="text-sm font-medium text-ink-muted hover:text-ink">
            {t("letters.review")}
          </button>
        </div>
      </td>
    </tr>
  );
}

function ReviewLetterModal({ letter, onClose }: { letter: ExplanationLetterResponse; onClose: () => void }) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const [comment, setComment] = useState(letter.hr_comment ?? "");
  const [error, setError] = useState<string | null>(null);

  async function downloadAttachment() {
    await explanationLettersApi.downloadAttachment(letter.id, `explanation-${letter.employee.employee_id}-${letter.date}`);
  }

  const reviewMutation = useMutation({
    mutationFn: () => explanationLettersApi.review(letter.id, comment),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["explanation-letters"] });
      onClose();
    },
    onError: (err: unknown) => setError(getErrorMessage(err)),
  });

  return (
    <Modal title={t("letters.reviewTitle", { name: letter.employee.full_name })} onClose={onClose}>
      <div className="space-y-4">
        <div className="rounded-lg bg-canvas p-3 text-sm text-ink-muted">
          {/* One flowing translated sentence rather than a styled sub-span, since
              word order for "late by X on date" differs across languages - a fixed
              mid-sentence styled span would assume an order that doesn't hold for all three. */}
          {t("letters.arrivedLate", { minutes: letter.late_minutes, date: formatDateShort(letter.date) })}
        </div>
        <div>
          <Label>{t("letters.employeeExplanation")}</Label>
          <p className="rounded-lg border border-line bg-canvas px-3 py-2 text-sm text-ink">
            {letter.employee_explanation || t("letters.notSubmittedYet")}
          </p>
        </div>
        <div>
          <Label>{t("letters.viewAttachment")}</Label>
          {letter.attachment_url ? (
            <button
              type="button"
              onClick={() => void downloadAttachment()}
              className="flex items-center gap-1 text-sm font-medium text-brand hover:text-brand-hover"
            >
              <Paperclip size={14} /> {t("letters.viewAttachment")}
            </button>
          ) : (
            <p className="text-sm text-ink-muted">{t("letters.noAttachment")}</p>
          )}
        </div>
        <div>
          <Label htmlFor="comment">{t("letters.hrComment")}</Label>
          <Textarea
            id="comment"
            rows={4}
            value={comment}
            onChange={(event) => setComment(event.target.value)}
            placeholder={t("letters.hrCommentPlaceholder") ?? undefined}
          />
        </div>
        {error && <p className="text-sm text-status-danger">{error}</p>}
        <div className="flex justify-end gap-2 border-t border-line pt-4">
          <Button type="button" variant="secondary" onClick={onClose}>
            {t("common.cancel")}
          </Button>
          <Button
            type="button"
            onClick={() => {
              setError(null);
              reviewMutation.mutate();
            }}
            disabled={!comment.trim() || reviewMutation.isPending}
          >
            {reviewMutation.isPending ? t("common.saving") : t("letters.saveReview")}
          </Button>
        </div>
      </div>
    </Modal>
  );
}
