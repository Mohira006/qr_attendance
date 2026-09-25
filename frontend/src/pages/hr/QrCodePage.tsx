import { Printer } from "lucide-react";
import { useTranslation } from "react-i18next";
import { QRCodeSVG } from "qrcode.react";

import { Button } from "@/components/ui/Button";
import { Card, CardBody } from "@/components/ui/Card";

export function QrCodePage() {
  const { t } = useTranslation();
  const scanUrl = `${window.location.origin}/scan`;

  return (
    <div className="max-w-md space-y-6">
      <div className="print:hidden">
        <h1 className="font-display text-2xl font-semibold text-ink">{t("qrCode.title")}</h1>
        <p className="text-sm text-ink-muted">{t("qrCode.subtitle")}</p>
      </div>

      <Card>
        <CardBody className="flex flex-col items-center gap-4 py-10">
          <QRCodeSVG value={scanUrl} size={240} level="M" marginSize={2} />
          <p className="break-all text-center text-xs text-ink-faint">{scanUrl}</p>
        </CardBody>
      </Card>

      <div className="print:hidden">
        <p className="mb-4 text-sm text-ink-muted">{t("qrCode.instructions")}</p>
        <Button onClick={() => window.print()}>
          <Printer size={16} className="mr-1.5" /> {t("qrCode.print")}
        </Button>
      </div>
    </div>
  );
}
