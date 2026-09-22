"use client";

import { useState, useTransition } from "react";
import { Info, RotateCcw, Save } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { updateAutomationSetting, resetAutomationSetting } from "@/lib/actions";
import type { AutomationSetting } from "@/lib/types";

/** One editable automation tunable - renders itself from the setting's own
 * `type`, same "backend registry drives the UI" pattern as review-item-card
 * rendering any automation's actions from its registered kind. A brand-new
 * setting (app/automations/settings_registry.py) shows up here with zero
 * frontend changes. */
export function AutomationSettingField({ setting }: { setting: AutomationSetting }) {
  const [value, setValue] = useState(setting.value);
  const [pending, startTransition] = useTransition();

  function save(next: boolean | number | string = value) {
    startTransition(async () => {
      try {
        await updateAutomationSetting(setting.key, next);
        toast.success(`${setting.label} updated`);
      } catch (e) {
        toast.error(e instanceof Error ? e.message : "Couldn't save that setting");
      }
    });
  }

  function reset() {
    startTransition(async () => {
      try {
        await resetAutomationSetting(setting.key);
        setValue(setting.default);
        toast.success(`${setting.label} reset to default`);
      } catch (e) {
        toast.error(e instanceof Error ? e.message : "Couldn't reset that setting");
      }
    });
  }

  return (
    <div className="flex flex-col gap-2 border-b border-border/60 py-3.5 last:border-b-0">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <Label className="text-xs font-bold text-foreground">{setting.label}</Label>
          {setting.description && (
            <TooltipProvider delay={100}>
              <Tooltip>
                <TooltipTrigger className="inline-flex size-4 items-center justify-center rounded-full text-muted-foreground/70 hover:text-foreground transition-colors cursor-help">
                  <Info className="size-3.5" />
                </TooltipTrigger>
                <TooltipContent side="top" className="max-w-xs text-xs font-normal">
                  {setting.description}
                </TooltipContent>
              </Tooltip>
            </TooltipProvider>
          )}
          {setting.is_overridden && (
            <Badge variant="secondary" className="text-[10px] font-semibold">
              Customized
            </Badge>
          )}
        </div>
        {setting.is_overridden && (
          <Button size="sm" variant="outline" disabled={pending} onClick={reset}>
            <RotateCcw className="size-3.5" />
            Reset to default ({String(setting.default)})
          </Button>
        )}
      </div>

      {setting.type === "bool" && (
        <label className="flex w-fit items-center gap-2 text-xs font-medium text-foreground">
          <input
            type="checkbox"
            className="size-4"
            checked={Boolean(value)}
            disabled={pending}
            onChange={(e) => {
              setValue(e.target.checked);
              save(e.target.checked);
            }}
          />
          {value ? "Enabled" : "Disabled"}
        </label>
      )}

      {(setting.type === "int" || setting.type === "float") && (
        <div className="flex items-center gap-2">
          <Input
            type="number"
            className="h-8 w-32 text-sm"
            step={setting.type === "float" ? 0.01 : 1}
            min={setting.min ?? undefined}
            max={setting.max ?? undefined}
            value={String(value)}
            disabled={pending}
            onChange={(e) => setValue(e.target.valueAsNumber)}
          />
          <Button size="sm" disabled={pending || value === setting.value} onClick={() => save()}>
            <Save className="size-3.5" />
            Save
          </Button>
        </div>
      )}

      {(setting.type === "csv" || setting.type === "text") && (
        <div className="flex items-center gap-2">
          <Input
            className="h-8 flex-1 text-sm"
            placeholder={setting.type === "csv" ? "comma-separated addresses…" : "…"}
            value={String(value)}
            disabled={pending}
            onChange={(e) => setValue(e.target.value)}
          />
          <Button size="sm" disabled={pending || value === setting.value} onClick={() => save()}>
            <Save className="size-3.5" />
            Save
          </Button>
        </div>
      )}
    </div>
  );
}
