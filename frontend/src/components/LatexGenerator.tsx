import { useEffect, useMemo, useState } from "react";
import type { FormEvent } from "react";
import { generateLatex, fetchLatexSettings } from "../api";
import {
  LatexGenerationRequest,
  LatexGenerationResult,
  LatexSettings,
} from "../types";
import "./LatexGenerator.css";

interface LatexGeneratorProps {
  apiBase: string;
}

type GenerationPhase = "idle" | "loading" | "success" | "error";

interface FormState {
  dataFileName: string;
  latexTextName: string;
  latexFileName: string;
  latexCommandText: string;
  fetchCards: boolean;
  fetchFromScratch: boolean;
  downloadImages: boolean;
  skipCompile: boolean;
}

function normaliseCommand(text: string): string[] | undefined {
  const tokens = text
    .split(/\r?\n/)
    .map((token) => token.trim())
    .filter(Boolean);
  return tokens.length ? tokens : undefined;
}

export function LatexGenerator({ apiBase }: LatexGeneratorProps) {
  const [settings, setSettings] = useState<LatexSettings | null>(null);
  const [form, setForm] = useState<FormState | null>(null);
  const [phase, setPhase] = useState<GenerationPhase>("idle");
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<LatexGenerationResult | null>(null);

  useEffect(() => {
    let cancelled = false;
    fetchLatexSettings()
      .then((data) => {
        if (cancelled) {
          return;
        }
        setSettings(data);
        setForm({
          dataFileName: data.dataFileName,
          latexTextName: data.latexTextName,
          latexFileName: data.latexFileName,
          latexCommandText: data.latexCommand.join("\n"),
          fetchCards: false,
          fetchFromScratch: false,
          downloadImages: true,
          skipCompile: false,
        });
      })
      .catch((err: Error) => {
        if (!cancelled) {
          setError(err.message);
          setPhase("error");
        }
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const pdfDownloadUrl = useMemo(() => {
    if (!result?.pdfPath) {
      return null;
    }
    const params = new URLSearchParams({ path: result.pdfPath });
    return `${apiBase}/latex/download?${params.toString()}`;
  }, [apiBase, result]);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!form) {
      return;
    }

    setPhase("loading");
    setError(null);
    setResult(null);

    const payload: LatexGenerationRequest = {
      dataFileName: form.dataFileName,
      latexTextName: form.latexTextName,
      latexFileName: form.latexFileName,
      latexCommand: normaliseCommand(form.latexCommandText),
      fetchCards: form.fetchCards,
      fetchFromScratch: form.fetchFromScratch,
      downloadImages: form.downloadImages,
      skipCompile: form.skipCompile,
    };

    try {
      const response = await generateLatex(payload);
      setResult(response);
      setPhase("success");
    } catch (err) {
      const message = err instanceof Error ? err.message : "未知错误";
      setError(message);
      setPhase("error");
    }
  };

  const handleChange = <K extends keyof FormState>(key: K, value: FormState[K]) => {
    setForm((prev) => {
      if (!prev) {
        return prev;
      }
      const next = { ...prev, [key]: value };
      if (key === "fetchFromScratch" && value) {
        next.fetchCards = true;
        next.downloadImages = true;
      }
      return next;
    });
  };

  if (!form) {
    return (
      <section className="latex-panel">
        <header className="latex-panel__header">
          <h2>LaTeX 生成</h2>
          <p>正在加载配置…</p>
        </header>
        {error && <div className="latex-panel__error">加载失败：{error}</div>}
      </section>
    );
  }

  return (
    <section className="latex-panel">
      <header className="latex-panel__header">
        <div>
          <h2>LaTeX 生成</h2>
          <p>调整生成参数并直接在浏览器中触发 PDF 编译。</p>
        </div>
        {settings && (
          <span className="latex-panel__hint">
            默认命令：{settings.latexCommand.join(" ")}
          </span>
        )}
      </header>

      <form className="latex-form" onSubmit={handleSubmit}>
        <div className="latex-form__grid">
          <label>
            <span>卡牌数据 JSON 文件</span>
            <input
              type="text"
              value={form.dataFileName}
              onChange={(event) => handleChange("dataFileName", event.target.value)}
              required
            />
          </label>
          <label>
            <span>LaTeX 文本输出路径</span>
            <input
              type="text"
              value={form.latexTextName}
              onChange={(event) => handleChange("latexTextName", event.target.value)}
              required
            />
          </label>
          <label>
            <span>LaTeX 主文件路径</span>
            <input
              type="text"
              value={form.latexFileName}
              onChange={(event) => handleChange("latexFileName", event.target.value)}
              required
            />
          </label>
          <label className="latex-form__command">
            <span>编译命令（每行一个参数）</span>
            <textarea
              value={form.latexCommandText}
              onChange={(event) => handleChange("latexCommandText", event.target.value)}
              rows={settings?.latexCommand.length ?? 4}
              placeholder={settings?.latexCommand.join("\n")}
            />
          </label>
        </div>

        <fieldset className="latex-form__options">
          <legend>可选步骤</legend>
          <label>
            <input
              type="checkbox"
              checked={form.fetchCards}
              onChange={(event) => handleChange("fetchCards", event.target.checked)}
            />
            抓取最新卡牌数据
          </label>
          <label>
            <input
              type="checkbox"
              checked={form.fetchFromScratch}
              onChange={(event) => handleChange("fetchFromScratch", event.target.checked)}
            />
            重新生成数据文件（会同时抓取数据）
          </label>
          <label>
            <input
              type="checkbox"
              checked={form.downloadImages}
              onChange={(event) => handleChange("downloadImages", event.target.checked)}
              disabled={!form.fetchCards && !form.fetchFromScratch}
            />
            下载缺失的卡图
          </label>
          <label>
            <input
              type="checkbox"
              checked={form.skipCompile}
              onChange={(event) => handleChange("skipCompile", event.target.checked)}
            />
            仅生成 LaTeX 文本（跳过 PDF 编译）
          </label>
        </fieldset>

        <div className="latex-form__actions">
          <button type="submit" disabled={phase === "loading"}>
            {phase === "loading" ? "正在执行…" : "生成 PDF"}
          </button>
          {error && <span className="latex-panel__error">{error}</span>}
        </div>
      </form>

      {result && (
        <section className="latex-result" aria-live="polite">
          <header>
            <h3>生成结果</h3>
          </header>
          <dl>
            <div>
              <dt>LaTeX 文本</dt>
              <dd>{result.latexTextPath}</dd>
            </div>
            <div>
              <dt>编译命令</dt>
              <dd>{result.command.join(" ")}</dd>
            </div>
            {result.pdfPath && (
              <div>
                <dt>PDF 文件</dt>
                <dd>
                  {pdfDownloadUrl ? (
                    <a href={pdfDownloadUrl} target="_blank" rel="noreferrer">
                      下载 / 查看
                    </a>
                  ) : (
                    result.pdfPath
                  )}
                </dd>
              </div>
            )}
          </dl>
          {(result.stdout || result.stderr) && (
            <details className="latex-result__logs" open>
              <summary>查看编译日志</summary>
              {result.stdout && (
                <pre>
                  <strong>STDOUT</strong>
                  {"\n"}
                  {result.stdout}
                </pre>
              )}
              {result.stderr && (
                <pre>
                  <strong>STDERR</strong>
                  {"\n"}
                  {result.stderr}
                </pre>
              )}
            </details>
          )}
        </section>
      )}
    </section>
  );
}
