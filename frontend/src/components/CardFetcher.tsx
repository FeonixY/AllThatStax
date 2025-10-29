import { FormEvent, useEffect, useState } from "react";
import {
  fetchCardFetchSettings,
  triggerCardFetch,
} from "../api";
import {
  CardFetchRequest,
  CardFetchResponse,
  CardFetchSettings,
} from "../types";
import "./CardFetcher.css";

interface CardFetcherProps {
  apiBase: string;
}

type FetchPhase = "idle" | "loading" | "success" | "error";

interface FormState {
  cardListName: string;
  dataFileName: string;
  imageFolderName: string;
  fromScratch: boolean;
  downloadImages: boolean;
}

export function CardFetcher({ apiBase }: CardFetcherProps) {
  const [settings, setSettings] = useState<CardFetchSettings | null>(null);
  const [form, setForm] = useState<FormState | null>(null);
  const [phase, setPhase] = useState<FetchPhase>("idle");
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<CardFetchResponse | null>(null);

  useEffect(() => {
    let cancelled = false;
    fetchCardFetchSettings()
      .then((data) => {
        if (cancelled) {
          return;
        }
        setSettings(data);
        setForm({
          cardListName: data.cardListName,
          dataFileName: data.dataFileName,
          imageFolderName: data.imageFolderName,
          fromScratch: false,
          downloadImages: data.downloadImages,
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

  const handleChange = <K extends keyof FormState>(key: K, value: FormState[K]) => {
    setForm((prev) => {
      if (!prev) {
        return prev;
      }
      const next = { ...prev, [key]: value };
      if (key === "fromScratch" && value) {
        next.downloadImages = true;
      }
      return next;
    });
  };

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!form) {
      return;
    }
    const payload: CardFetchRequest = {
      cardListName: form.cardListName,
      dataFileName: form.dataFileName,
      imageFolderName: form.imageFolderName,
      fromScratch: form.fromScratch,
      downloadImages: form.downloadImages,
    };

    setPhase("loading");
    setError(null);
    setResult(null);

    try {
      const response = await triggerCardFetch(payload);
      setResult(response);
      setPhase("success");
    } catch (err) {
      const message = err instanceof Error ? err.message : "未知错误";
      setError(message);
      setPhase("error");
    }
  };

  if (!form) {
    return (
      <section className="fetch-panel">
        <header className="fetch-panel__header">
          <h2>卡牌信息爬取</h2>
          <p>正在加载配置…</p>
        </header>
        {error && <div className="fetch-panel__error">加载失败：{error}</div>}
      </section>
    );
  }

  return (
    <section className="fetch-panel">
      <header className="fetch-panel__header">
        <div>
          <h2>卡牌信息爬取</h2>
          <p>
            读取牌表并使用 Scryfall 获取英文数据与卡图，同时从 mtgch.com 获取中文信息。
          </p>
        </div>
        {settings && (
          <span className="fetch-panel__hint">
            默认设置来自 {apiBase || "本地服务"}
          </span>
        )}
      </header>

      <form className="fetch-form" onSubmit={handleSubmit}>
        <div className="fetch-form__grid">
          <label>
            <span>卡表列表文件</span>
            <input
              type="text"
              value={form.cardListName}
              onChange={(event) => handleChange("cardListName", event.target.value)}
              required
            />
          </label>
          <label>
            <span>数据输出 JSON</span>
            <input
              type="text"
              value={form.dataFileName}
              onChange={(event) => handleChange("dataFileName", event.target.value)}
              required
            />
          </label>
          <label>
            <span>卡图目录</span>
            <input
              type="text"
              value={form.imageFolderName}
              onChange={(event) => handleChange("imageFolderName", event.target.value)}
              required
            />
          </label>
        </div>

        <fieldset className="fetch-form__options">
          <legend>选项</legend>
          <label>
            <input
              type="checkbox"
              checked={form.fromScratch}
              onChange={(event) => handleChange("fromScratch", event.target.checked)}
            />
            从空白开始重新生成（忽略已有数据）
          </label>
          <label>
            <input
              type="checkbox"
              checked={form.downloadImages}
              onChange={(event) => handleChange("downloadImages", event.target.checked)}
              disabled={form.fromScratch}
            />
            下载英文卡图
          </label>
        </fieldset>

        <div className="fetch-form__actions">
          <button type="submit" disabled={phase === "loading"}>
            {phase === "loading" ? "正在抓取…" : "开始抓取"}
          </button>
          {error && <span className="fetch-panel__error">{error}</span>}
        </div>
      </form>

      {result && (
        <section className="fetch-result" aria-live="polite">
          <header>
            <h3>抓取结果</h3>
          </header>
          <dl>
            <div>
              <dt>处理卡牌</dt>
              <dd>
                {result.cardsUpdated}/{result.cardsProcessed}
              </dd>
            </div>
            <div>
              <dt>下载卡图</dt>
              <dd>{result.imagesDownloaded}</dd>
            </div>
            <div>
              <dt>耗时</dt>
              <dd>{result.duration.toFixed(1)} 秒</dd>
            </div>
            <div>
              <dt>数据文件</dt>
              <dd>{result.dataFile}</dd>
            </div>
          </dl>
          {!!result.errors.length && (
            <details className="fetch-result__errors">
              <summary>查看失败记录（{result.errors.length}）</summary>
              <ul>
                {result.errors.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            </details>
          )}
        </section>
      )}
    </section>
  );
}
