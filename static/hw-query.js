/*
 * HWGI Query Assistant — Frontend logic
 *
 * 백엔드 API:
 *   GET  /health                   {ok, model, base_url, dbms[]}
 *   POST /api/query/generate       GenerateRequest → GenerateResponse
 *
 * 에러 매핑:
 *   422 — Pydantic 입력 검증 실패 (DBMS enum, 빈 문자열 등)
 *   502 — LLM 외부 의존 실패 또는 사후 안전 검증(safety) 실패
 */
(() => {
  "use strict";

  const API = {
    HEALTH: "/health",
    GENERATE: "/api/query/generate",
  };

  // DBMS 별 예시 스키마 (보험 도메인 CONTRACT 패턴, prompts.py few-shot 과 정합).
  const SCHEMA_TEMPLATES = {
    oracle:
      "CONTRACT(\n" +
      "  POL_NO       VARCHAR2(20)  PK   -- 증권번호\n" +
      "  REG_DATE     DATE                -- 계약일\n" +
      "  REGION       VARCHAR2(20)        -- 계약 지역\n" +
      "  PRODUCT_CD   VARCHAR2(10)        -- 상품코드\n" +
      "  PREMIUM      NUMBER              -- 보험료\n" +
      "  STATUS       VARCHAR2(10)        -- 계약 상태 (ACTIVE/CANCEL/EXPIRED)\n" +
      ")\n",
    mssql:
      "CONTRACT(\n" +
      "  POL_NO       VARCHAR(20)   PK   -- 증권번호\n" +
      "  REG_DATE     DATETIME             -- 계약일\n" +
      "  REGION       NVARCHAR(20)         -- 계약 지역\n" +
      "  PRODUCT_CD   NVARCHAR(10)         -- 상품코드\n" +
      "  PREMIUM      DECIMAL(18,2)        -- 보험료\n" +
      "  STATUS       NVARCHAR(10)         -- 계약 상태 (ACTIVE/CANCEL/EXPIRED)\n" +
      ")\n",
    greenplum:
      "CONTRACT(\n" +
      "  POL_NO       VARCHAR(20)   PK   -- 증권번호\n" +
      "  REG_DATE     DATE                 -- 계약일\n" +
      "  REGION       VARCHAR(20)          -- 계약 지역\n" +
      "  PRODUCT_CD   VARCHAR(10)          -- 상품코드\n" +
      "  PREMIUM      NUMERIC(18,2)        -- 보험료\n" +
      "  STATUS       VARCHAR(10)          -- 계약 상태 (ACTIVE/CANCEL/EXPIRED)\n" +
      ") DISTRIBUTED BY (POL_NO);\n",
    tibero:
      "CONTRACT(\n" +
      "  POL_NO       VARCHAR2(20)  PK   -- 증권번호\n" +
      "  REG_DATE     DATE                -- 계약일\n" +
      "  REGION       VARCHAR2(20)        -- 계약 지역\n" +
      "  PRODUCT_CD   VARCHAR2(10)        -- 상품코드\n" +
      "  PREMIUM      NUMBER              -- 보험료 (Oracle 호환)\n" +
      "  STATUS       VARCHAR2(10)        -- 계약 상태\n" +
      ")\n",
  };

  const SAMPLE_QUESTION =
    "지난달 강원도에서 신규 계약된 건수와 평균 보험료를 알려줘.";

  // ─── DOM ─────────────────────────────────────────────────────────
  const $ = (id) => document.getElementById(id);

  const els = {
    modelBadge: $("modelBadge"),
    dbmsBadge: $("dbmsBadge"),
    resetBtn: $("resetBtn"),
    segBtns: document.querySelectorAll(".seg__btn"),
    templateBtn: $("templateBtn"),
    schemaInput: $("schemaInput"),
    questionInput: $("questionInput"),
    schemaCount: $("schemaCount"),
    questionCount: $("questionCount"),
    generateBtn: $("generateBtn"),
    clearBtn: $("clearBtn"),
    resultEmpty: $("resultEmpty"),
    resultBody: $("resultBody"),
    resultError: $("resultError"),
    resultActions: $("resultActions"),
    resultMeta: $("resultMeta"),
    resultSql: $("resultSql"),
    resultAssumptions: $("resultAssumptions"),
    resultWarnings: $("resultWarnings"),
    assumptionsTitle: $("assumptionsTitle"),
    warningsTitle: $("warningsTitle"),
    sqlLinesCount: $("sqlLinesCount"),
    assumptionsCount: $("assumptionsCount"),
    warningsCount: $("warningsCount"),
    regenBtn: $("regenBtn"),
    copyBtn: $("copyBtn"),
    downloadBtn: $("downloadBtn"),
    toast: $("toast"),
  };

  // DBMS 배지 표시 이름 (HTML 의 SEG 버튼 텍스트와 일치)
  const DBMS_DISPLAY = {
    oracle: "Oracle",
    mssql: "MSSQL",
    greenplum: "Greenplum",
    tibero: "Tibero",
  };

  // 마지막 생성 결과 — 복사/다운로드 시 참조.
  let lastResult = null;
  let toastTimer = null;

  // ─── 헬퍼 ────────────────────────────────────────────────────────

  function getSelectedDbms() {
    const active = document.querySelector(".seg__btn.is-active");
    return active ? active.dataset.dbms : "oracle";
  }

  function selectDbms(dbms) {
    els.segBtns.forEach((btn) => {
      const isActive = btn.dataset.dbms === dbms;
      btn.classList.toggle("is-active", isActive);
      btn.setAttribute("aria-checked", isActive ? "true" : "false");
    });
    if (els.dbmsBadge) {
      els.dbmsBadge.textContent = DBMS_DISPLAY[dbms] || dbms;
    }
  }

  function updateInputCounts() {
    const s = els.schemaInput.value.length;
    const q = els.questionInput.value.length;
    els.schemaCount.textContent = `${s.toLocaleString()}자`;
    els.questionCount.textContent = `${q.toLocaleString()}자`;
  }

  function updateResultMeta(data) {
    const sqlLines = data.sql ? data.sql.split("\n").length : 0;
    els.sqlLinesCount.textContent = `${sqlLines}줄`;
    els.assumptionsCount.textContent = `${(data.assumptions || []).length}개`;
    els.warningsCount.textContent = `${(data.warnings || []).length}개`;
    els.resultMeta.hidden = false;
  }

  function showToast(message) {
    els.toast.textContent = message;
    els.toast.hidden = false;
    requestAnimationFrame(() => els.toast.classList.add("is-visible"));
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => {
      els.toast.classList.remove("is-visible");
      setTimeout(() => { els.toast.hidden = true; }, 250);
    }, 2200);
  }

  function setLoading(isLoading) {
    els.generateBtn.classList.toggle("is-loading", isLoading);
    els.generateBtn.disabled = isLoading;
  }

  function clearResultUI() {
    els.resultEmpty.hidden = false;
    els.resultBody.hidden = true;
    els.resultError.hidden = true;
    els.resultActions.hidden = true;
    els.resultMeta.hidden = true;
    els.resultSql.textContent = "";
    els.resultAssumptions.innerHTML = "";
    els.resultWarnings.innerHTML = "";
    els.assumptionsTitle.hidden = true;
    els.warningsTitle.hidden = true;
    els.resultAssumptions.hidden = true;
    els.resultWarnings.hidden = true;
    lastResult = null;
  }

  function showError(message) {
    els.resultEmpty.hidden = true;
    els.resultBody.hidden = true;
    els.resultActions.hidden = true;
    els.resultError.textContent = message;
    els.resultError.hidden = false;
  }

  function renderList(ul, titleEl, items) {
    ul.innerHTML = "";
    if (!items || items.length === 0) {
      ul.hidden = true;
      titleEl.hidden = true;
      return;
    }
    for (const item of items) {
      const li = document.createElement("li");
      li.textContent = item;  // textContent 사용 — XSS 방지
      ul.appendChild(li);
    }
    ul.hidden = false;
    titleEl.hidden = false;
  }

  function renderResult(data) {
    lastResult = data;
    els.resultEmpty.hidden = true;
    els.resultError.hidden = true;
    els.resultBody.hidden = false;
    els.resultActions.hidden = false;
    els.resultSql.textContent = data.sql;
    renderList(els.resultAssumptions, els.assumptionsTitle, data.assumptions);
    renderList(els.resultWarnings, els.warningsTitle, data.warnings);
    updateResultMeta(data);
  }

  // ─── API 호출 ────────────────────────────────────────────────────

  async function fetchHealth() {
    try {
      const res = await fetch(API.HEALTH);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      els.modelBadge.textContent = data.model || "—";
      els.modelBadge.title = `LLM: ${data.model} · ${data.base_url}`;
    } catch (err) {
      els.modelBadge.textContent = "오프라인";
      els.modelBadge.title = String(err);
    }
  }

  async function callGenerate(payload) {
    let res;
    try {
      res = await fetch(API.GENERATE, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
    } catch (err) {
      throw { kind: "network", message: "백엔드에 연결할 수 없습니다. 서버 상태를 확인하세요." };
    }
    const text = await res.text();
    let body;
    try { body = text ? JSON.parse(text) : {}; }
    catch { body = { detail: text }; }

    if (res.ok) return body;

    if (res.status === 422) {
      // Pydantic 검증 실패 — detail 은 배열 형식.
      const messages = Array.isArray(body.detail)
        ? body.detail.map((d) => `${(d.loc || []).join(".")}: ${d.msg}`).join("\n")
        : String(body.detail || "입력값을 확인하세요.");
      throw { kind: "validation", message: messages };
    }
    if (res.status === 502) {
      throw {
        kind: "upstream",
        message:
          "AI 응답을 받지 못했습니다. 잠시 후 다시 시도하거나 질문을 좀 더 단순하게 다시 입력해 주세요.\n" +
          `(원인: ${body.detail || "알 수 없음"})`,
      };
    }
    throw { kind: "unknown", message: `예상치 못한 응답 (HTTP ${res.status}): ${body.detail || text}` };
  }

  // ─── 핸들러 ───────────────────────────────────────────────────────

  async function handleGenerate() {
    const dbms = getSelectedDbms();
    const schema_text = els.schemaInput.value.trim();
    const question = els.questionInput.value.trim();

    if (!schema_text) {
      showError("스키마를 입력하세요. (예시로 채우기 버튼을 활용할 수 있습니다)");
      els.schemaInput.focus();
      return;
    }
    if (!question) {
      showError("질문을 입력하세요.");
      els.questionInput.focus();
      return;
    }

    setLoading(true);
    els.resultError.hidden = true;
    try {
      const data = await callGenerate({ dbms, schema_text, question });
      renderResult(data);
    } catch (err) {
      showError(err.message || String(err));
    } finally {
      setLoading(false);
    }
  }

  function handleTemplate() {
    const dbms = getSelectedDbms();
    els.schemaInput.value = SCHEMA_TEMPLATES[dbms] || "";
    if (!els.questionInput.value.trim()) {
      els.questionInput.value = SAMPLE_QUESTION;
    }
    updateInputCounts();
    els.schemaInput.focus();
  }

  function handleClear() {
    els.schemaInput.value = "";
    els.questionInput.value = "";
    updateInputCounts();
    clearResultUI();
    els.schemaInput.focus();
  }

  // 헤더 "초기화" — 입력 비우기와 동일 동작이지만, 의도상 결과 영역 포커스가
  // 더 자연스러워 별도 핸들러로 분리(미세 차이만).
  function handleReset() {
    handleClear();
    showToast("입력과 결과를 초기화했습니다");
  }

  async function handleCopy() {
    if (!lastResult) return;
    try {
      await navigator.clipboard.writeText(lastResult.sql);
      showToast("SQL을 클립보드에 복사했습니다");
    } catch {
      // 클립보드 권한이 없는 경우 fallback — textarea 선택
      const ta = document.createElement("textarea");
      ta.value = lastResult.sql;
      ta.style.position = "fixed";
      ta.style.left = "-9999px";
      document.body.appendChild(ta);
      ta.select();
      try { document.execCommand("copy"); showToast("SQL을 복사했습니다"); }
      catch { showToast("복사 실패 — SQL을 직접 선택해 복사하세요"); }
      finally { document.body.removeChild(ta); }
    }
  }

  function handleDownload() {
    if (!lastResult) return;
    const ts = new Date().toISOString().replace(/[:T]/g, "-").slice(0, 19);
    const filename = `query_${lastResult.dbms}_${ts}.sql`;
    const header =
      `-- HWGI Query Assistant 생성 SQL\n` +
      `-- DBMS: ${lastResult.dbms}\n` +
      `-- 생성: ${new Date().toISOString()}\n` +
      `-- 주의: 실행 전 반드시 검토하세요.\n\n`;
    const blob = new Blob([header + lastResult.sql + "\n"], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    showToast(`${filename} 저장됨`);
  }

  // ─── 초기화 ───────────────────────────────────────────────────────

  function bindEvents() {
    els.segBtns.forEach((btn) =>
      btn.addEventListener("click", () => selectDbms(btn.dataset.dbms))
    );
    els.templateBtn.addEventListener("click", handleTemplate);
    els.generateBtn.addEventListener("click", handleGenerate);
    els.clearBtn.addEventListener("click", handleClear);
    els.resetBtn.addEventListener("click", handleReset);
    els.regenBtn.addEventListener("click", handleGenerate);
    els.copyBtn.addEventListener("click", handleCopy);
    els.downloadBtn.addEventListener("click", handleDownload);

    els.schemaInput.addEventListener("input", updateInputCounts);
    els.questionInput.addEventListener("input", updateInputCounts);

    // Ctrl/Cmd+Enter 로 빠른 생성
    document.addEventListener("keydown", (e) => {
      if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
        e.preventDefault();
        handleGenerate();
      }
    });
  }

  bindEvents();
  updateInputCounts();   // 초기값 0자 표시
  fetchHealth();
})();
