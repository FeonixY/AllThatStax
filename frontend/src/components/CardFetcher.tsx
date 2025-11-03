import { FormEvent, useEffect, useMemo, useRef, useState } from "react";
import {
  fetchCardFetchSettings,
  fetchMoxfieldDeck,
  startCardFetch,
} from "../api";
import {
  CardFetchJobState,
  CardFetchRequest,
  CardFetchSettings,
  MoxfieldFetchResponse,
  createInitialCardFetchJobState,
} from "../types";
import "./CardFetcher.css";

interface FormState {
  cardListName: string;
  dataFileName: string;
  imageFolderName: string;
  fromScratch: boolean;
  downloadImages: boolean;
}

type FetchPhase = "idle" | "loading" | "success" | "error";
type JobStateSetter = (
  value:
    | CardFetchJobState
    | ((prev: CardFetchJobState) => CardFetchJobState)
) => void;

interface CardFetcherProps {
  apiBase: string;
  jobState: CardFetchJobState;
  onJobStateChange: JobStateSetter;
}

export function CardFetcher({ apiBase, jobState, onJobStateChange }: CardFetcherProps) {
  const [settings, setSettings] = useState<CardFetchSettings | null>(null);
  const [form, setForm] = useState<FormState | null>(null);
  const [settingsError, setSettingsError] = useState<string | null>(null);
  const [fetchError, setFetchError] = useState<string | null>(null);
  const [moxfieldDeckUrl, setMoxfieldDeckUrl] = useState("");
  const [moxfieldPhase, setMoxfieldPhase] = useState<FetchPhase>("idle");
  const [moxfieldError, setMoxfieldError] = useState<string | null>(null);
  const [moxfieldResult, setMoxfieldResult] =
    useState<MoxfieldFetchResponse | null>(null);
  const logContainerRef = useRef<HTMLDivElement | null>(null);
  const timeFormatter = useMemo(
    () =>
      new Intl.DateTimeFormat(undefined, {
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit",
      }),
    []
  );

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
        setMoxfieldDeckUrl(data.moxfieldDeckUrl ?? "");
      })
      .catch((err: Error) => {
        if (!cancelled) {
          setSettingsError(err.message);
        }
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (!logContainerRef.current) {
      return;
    }
    logContainerRef.current.scrollTop = logContainerRef.current.scrollHeight;
  }, [jobState.logs]);

  useEffect(() => {
    if (fetchError && jobState.status !== "error") {
      setFetchError(null);
    }
  }, [fetchError, jobState.status]);

  const progressPercent = useMemo(() => {
    if (!jobState.total || jobState.total <= 0) {
      return 0;
    }
    return Math.min(100, Math.round((jobState.processed / jobState.total) * 100));
  }, [jobState.processed, jobState.total]);

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

    const previousState: CardFetchJobState = {
      ...jobState,
      logs: [...jobState.logs],
    };

    onJobStateChange(() => ({
      ...createInitialCardFetchJobState(),
      status: "running",
    }));
    setFetchError(null);

    try {
      const response = await startCardFetch(payload);
      onJobStateChange(response);
    } catch (err) {
      const message = err instanceof Error ? err.message : "未知错误";
      setFetchError(message);
      onJobStateChange(() => previousState);
    }
  };

  const handleMoxfieldFetch = async () => {
    if (!form) {
      return;
    }
    const trimmedUrl = moxfieldDeckUrl.trim();
    if (!trimmedUrl) {
      setMoxfieldError("请输入 Moxfield 牌表链接");
      setMoxfieldPhase("error");
      return;
    }

    setMoxfieldPhase("loading");
    setMoxfieldError(null);
    setMoxfieldResult(null);

    try {
      const response = await fetchMoxfieldDeck({
        deckUrl: trimmedUrl,
        cardListName: form.cardListName,
      });
      setMoxfieldResult(response);
      setMoxfieldPhase("success");
    } catch (err) {
      const message = err instanceof Error ? err.message : "未知错误";
      setMoxfieldError(message);
      setMoxfieldPhase("error");
    }
  };

  if (!form) {
    return (
      <section className="fetch-panel">
        <header className="fetch-panel__header">
          <h2>卡牌信息爬取</h2>
          <p>正在加载配置…</p>
        </header>
        {settingsError && (
          <div className="fetch-panel__error">加载失败：{settingsError}</div>
        )}
      </section>
    );
  }

  const combinedError = fetchError || jobState.error || null;
  const result = jobState.result ?? null;

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
        <section className="fetch-moxfield">
          <header>
            <h3>从 Moxfield 获取牌表</h3>
            <p>将远程牌表保存为本地卡表列表文件，供后续抓取使用。</p>
          </header>
          <div className="fetch-moxfield__controls">
            <label>
              <span>Moxfield 牌表链接</span>
              <input
                type="text"
                value={moxfieldDeckUrl}
                onChange={(event) => setMoxfieldDeckUrl(event.target.value)}
                placeholder="https://moxfield.com/decks/..."
              />
            </label>
            <button
              type="button"
              className="fetch-button"
              onClick={handleMoxfieldFetch}
              disabled={moxfieldPhase === "loading"}
            >
              {moxfieldPhase === "loading" ? "正在获取…" : "获取牌表"}
            </button>
          </div>
          {moxfieldError && (
            <div className="fetch-panel__error">{moxfieldError}</div>
          )}
          {moxfieldResult && (
            <div className="fetch-moxfield__result" aria-live="polite">
              <p>
                成功写入 {moxfieldResult.cardsWritten} 张牌至{" "}
                <code>{moxfieldResult.cardListPath}</code>
              </p>
            </div>
          )}
        </section>

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
          <button
            type="submit"
            className="fetch-button"
            disabled={jobState.status === "running"}
          >
            {jobState.status === "running" ? "正在抓取…" : "开始抓取"}
          </button>
          {combinedError && (
            <span className="fetch-panel__error">{combinedError}</span>
          )}
        </div>
      </form>

      <section className="fetch-log">
        <header className="fetch-log__header">
          <div>
            <h3>抓取日志</h3>
            <p>实时追踪爬取进度与状态。</p>
          </div>
          <div className="fetch-log__summary">
            <span>
              已处理 {jobState.processed}
              {jobState.total ? ` / ${jobState.total}` : ""}
            </span>
            <span>更新 {jobState.updated}</span>
            <span>卡图 {jobState.imagesDownloaded}</span>
          </div>
        </header>
        <div className="fetch-log__progress" aria-hidden={jobState.total <= 0}>
          <div
            className="fetch-log__progress-bar"
            role="progressbar"
            aria-valuemin={0}
            aria-valuemax={100}
            aria-valuenow={progressPercent}
          >
            <div
              className="fetch-log__progress-fill"
              style={{ width: `${progressPercent}%` }}
            />
          </div>
          <span className="fetch-log__progress-label">
            {jobState.total > 0 ? `${progressPercent}%` : "等待开始"}
          </span>
        </div>
        <div className="fetch-log__body" ref={logContainerRef}>
          {jobState.logs.length ? (
            <ul className="fetch-log__list">
              {jobState.logs.map((entry) => (
                <li
                  key={entry.id}
                  className={`fetch-log__item fetch-log__item--${entry.level}`}
                >
                  <span className="fetch-log__time">
                    {timeFormatter.format(new Date(entry.timestamp * 1000))}
                  </span>
                  <div className="fetch-log__content">
                    <p className="fetch-log__message">{entry.message}</p>
                    <div className="fetch-log__meta">
                      {entry.cardName && (
                        <span>
                          {entry.cardName}
                          {entry.setCode ? ` (${entry.setCode})` : ""}
                        </span>
                      )}
                      {entry.total > 0 && (
                        <span>
                          进度 {entry.processed}/{entry.total}
                        </span>
                      )}
                    </div>
                  </div>
                </li>
              ))}
            </ul>
          ) : (
            <p className="fetch-log__empty">等待任务开始…</p>
          )}
        </div>
      </section>

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
