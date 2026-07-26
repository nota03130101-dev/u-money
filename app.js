const recordForm = document.querySelector("#recordForm");
const dateInput = document.querySelector("#dateInput");
const typeInput = document.querySelector("#typeInput");
const amountInput = document.querySelector("#amountInput");
const categoryInput = document.querySelector("#categoryInput");
const noteInput = document.querySelector("#noteInput");
const recordList = document.querySelector("#recordList");
const formMessage = document.querySelector("#formMessage");
const balanceAmount = document.querySelector("#balanceAmount");
const incomeAmount = document.querySelector("#incomeAmount");
const expenseAmount = document.querySelector("#expenseAmount");
const submitButton = document.querySelector("#submitButton");
const authStatus = document.querySelector("#authStatus");
const authMessage = document.querySelector("#authMessage");
const emailInput = document.querySelector("#emailInput");
const passwordInput = document.querySelector("#passwordInput");
const signInButton = document.querySelector("#signInButton");
const signUpButton = document.querySelector("#signUpButton");
const signOutButton = document.querySelector("#signOutButton");
const monthFilter = document.querySelector("#monthFilter");
const typeFilter = document.querySelector("#typeFilter");
const categoryFilter = document.querySelector("#categoryFilter");
const keywordFilter = document.querySelector("#keywordFilter");
const clearFiltersButton = document.querySelector("#clearFiltersButton");
const monthIncomeAmount = document.querySelector("#monthIncomeAmount");
const monthExpenseAmount = document.querySelector("#monthExpenseAmount");
const monthBalanceAmount = document.querySelector("#monthBalanceAmount");
const selectedMonthLabel = document.querySelector("#selectedMonthLabel");
const expenseChart = document.querySelector("#expenseChart");
const recordCount = document.querySelector("#recordCount");
const exportButton = document.querySelector("#exportButton");
const aiParseForm = document.querySelector("#aiParseForm");
const aiTextInput = document.querySelector("#aiTextInput");
const aiParseButton = document.querySelector("#aiParseButton");
const aiEnabledToggle = document.querySelector("#aiEnabledToggle");
const aiMessage = document.querySelector("#aiMessage");
const aiCandidateArea = document.querySelector("#aiCandidateArea");
const aiCandidateList = document.querySelector("#aiCandidateList");
const confirmAiCandidatesButton = document.querySelector("#confirmAiCandidatesButton");
const cancelAiCandidatesButton = document.querySelector("#cancelAiCandidatesButton");
const aiMonthlySummaryButton = document.querySelector("#aiMonthlySummaryButton");
const aiMonthlySummaryMessage = document.querySelector("#aiMonthlySummaryMessage");
const aiMonthlySummaryContent = document.querySelector("#aiMonthlySummaryContent");
const aiMonthlySummaryMeta = document.querySelector("#aiMonthlySummaryMeta");
const aiMonthlySummaryText = document.querySelector("#aiMonthlySummaryText");

const storageKey = "uMoneyRecords";
const aiPreferenceKey = "uMoneyAiEnabled";
const supabaseUrl = "https://bgdphvfukmpyyiiylwcu.supabase.co";
const supabaseKey = "sb_publishable__CKu_wgZzkruoKgrUywMPA_QuZHdgNr";
const supabaseClient = window.supabase
  ? window.supabase.createClient(supabaseUrl, supabaseKey)
  : null;
let records = [];
let editingIndex = null;
let currentUser = null;
let isCloudMode = false;
let cloudRecordsReady = false;
let aiCandidates = [];
let monthlyAiSummary = null;
let aiEnabled = localStorage.getItem(aiPreferenceKey) !== "false";

const localAiServiceUrl = ["localhost", "127.0.0.1"].includes(window.location.hostname)
  ? "http://127.0.0.1:8000"
  : "";
const aiServiceUrl = window.UMONEY_AI_SERVICE_URL || localAiServiceUrl;

monthFilter.value = getLocalDateString().slice(0, 7);
aiEnabledToggle.checked = aiEnabled;

function formatMoney(amount, type) {
  const sign = type === "收入" ? "+" : "-";
  return `${sign}¥${amount.toFixed(2)}`;
}

function formatTotalMoney(amount) {
  if (amount < 0) {
    return `-¥${Math.abs(amount).toFixed(2)}`;
  }

  return `¥${amount.toFixed(2)}`;
}

function showMessage(text, isSuccess = false) {
  formMessage.textContent = text;
  formMessage.classList.toggle("success", isSuccess);
}

function showAuthMessage(text, isSuccess = false) {
  authMessage.textContent = text;
  authMessage.classList.toggle("success", isSuccess);
}

function showAiMessage(text, isSuccess = false) {
  aiMessage.textContent = text;
  aiMessage.classList.toggle("success", isSuccess);
}

function showMonthlySummaryMessage(text, isSuccess = false) {
  aiMonthlySummaryMessage.textContent = text;
  aiMonthlySummaryMessage.classList.toggle("success", isSuccess);
}

function getLocalDateString() {
  const now = new Date();
  const localNow = new Date(now.getTime() - now.getTimezoneOffset() * 60 * 1000);
  return localNow.toISOString().slice(0, 10);
}

function updateAiAvailability() {
  const aiAvailable = aiEnabled && Boolean(aiServiceUrl);
  aiParseButton.disabled = !aiAvailable;
  aiMonthlySummaryButton.disabled = !aiAvailable;

  if (!aiEnabled) {
    aiCandidates = [];
    monthlyAiSummary = null;
    renderAiCandidates();
    renderMonthlyAiSummary();
    showAiMessage("AI 辅助已关闭，普通手动记账仍可使用。", true);
    showMonthlySummaryMessage("AI 月度总结已关闭，普通月度统计仍可使用。", true);
    return;
  }

  if (!aiServiceUrl) {
    showAiMessage("智能服务尚未配置，仍可使用普通手动记账。");
    showMonthlySummaryMessage("智能服务尚未配置，普通月度统计仍可使用。");
  }
}

function updateAuthView(user) {
  const previousUserId = currentUser?.id;
  const isLoggedIn = Boolean(user);
  currentUser = user || null;
  isCloudMode = isLoggedIn && Boolean(supabaseClient);
  cloudRecordsReady = false;

  if (previousUserId && previousUserId !== currentUser?.id) {
    aiCandidates = [];
    renderAiCandidates();
    monthlyAiSummary = null;
    renderMonthlyAiSummary();
  }

  authStatus.textContent = isLoggedIn
    ? `已登录：${user.email}。账单正在使用云端同步。`
    : "未登录。当前账单只保存在这个浏览器。";
  signInButton.hidden = isLoggedIn;
  signUpButton.hidden = isLoggedIn;
  signOutButton.hidden = !isLoggedIn;
  emailInput.disabled = isLoggedIn;
  passwordInput.disabled = isLoggedIn;
}

function saveRecords() {
  localStorage.setItem(storageKey, JSON.stringify(records));
}

function saveLocalRecords() {
  if (!isCloudMode) {
    saveRecords();
  }
}

function loadRecords() {
  const savedRecords = localStorage.getItem(storageKey);
  records = [];

  if (!savedRecords) {
    return;
  }

  try {
    const parsedRecords = JSON.parse(savedRecords);
    records = Array.isArray(parsedRecords) ? parsedRecords : [];
  } catch (error) {
    records = [];
    localStorage.removeItem(storageKey);
  }
}

function normalizeCloudRecord(record) {
  return {
    id: record.id,
    date: record.date,
    type: record.type,
    amount: Number(record.amount),
    category: record.category,
    note: record.note || "",
  };
}

async function loadCloudRecords() {
  if (!supabaseClient || !currentUser) {
    return;
  }

  showMessage("正在读取云端账单...", true);

  const { data, error } = await supabaseClient
    .from("records")
    .select("id, date, type, amount, category, note, created_at")
    .order("created_at", { ascending: true });

  if (error) {
    showMessage("读取云端账单失败，请检查网络或重新登录后再试。");
    return;
  }

  records = data.map(normalizeCloudRecord);
  cloudRecordsReady = true;
  editingIndex = null;
  submitButton.textContent = "添加记录";
  recordForm.reset();
  refreshView();
  showMessage("云端账单已同步。", true);
}

function loadLocalRecords() {
  loadRecords();
  editingIndex = null;
  submitButton.textContent = "添加记录";
  recordForm.reset();
  refreshView();
}

function getSelectedMonthRecords() {
  if (!monthFilter.value) {
    return records;
  }

  return records.filter((record) => record.date.startsWith(monthFilter.value));
}

function getPreviousMonth(month) {
  const [year, monthNumber] = month.split("-").map(Number);
  const previous = new Date(year, monthNumber - 2, 1);
  return `${previous.getFullYear()}-${String(previous.getMonth() + 1).padStart(2, "0")}`;
}

function calculateMonthAggregate(month) {
  const monthRecords = month
    ? records.filter((record) => record.date.startsWith(month))
    : records;
  const categoryTotals = {};
  let income = 0;
  let expense = 0;

  monthRecords.forEach((record) => {
    if (record.type === "收入") {
      income += record.amount;
      return;
    }

    expense += record.amount;
    categoryTotals[record.category] = (categoryTotals[record.category] || 0) + record.amount;
  });

  const expenseCategories = Object.entries(categoryTotals)
    .sort((first, second) => second[1] - first[1])
    .map(([category, amount]) => ({
      category,
      amount: amount.toFixed(2),
      percentage: Number(((amount / expense) * 100).toFixed(2)),
    }));
  const lastDay = month
    ? new Date(Number(month.slice(0, 4)), Number(month.slice(5, 7)), 0).getDate()
    : null;

  return {
    month,
    statistics_period_start: month ? `${month}-01` : null,
    statistics_period_end: month ? `${month}-${String(lastDay).padStart(2, "0")}` : null,
    totals: {
      income: income.toFixed(2),
      expense: expense.toFixed(2),
      balance_change: (income - expense).toFixed(2),
      record_count: monthRecords.length,
    },
    expense_categories: expenseCategories,
  };
}

function buildMonthlySummaryRequest() {
  if (!monthFilter.value) {
    return null;
  }

  const current = calculateMonthAggregate(monthFilter.value);
  const previousMonth = getPreviousMonth(monthFilter.value);
  const previous = calculateMonthAggregate(previousMonth);
  const hasPreviousData = previous.totals.record_count > 0;

  return {
    ...current,
    comparison: {
      previous_month: previousMonth,
      available: hasPreviousData,
      income_change: hasPreviousData
        ? (Number(current.totals.income) - Number(previous.totals.income)).toFixed(2)
        : null,
      expense_change: hasPreviousData
        ? (Number(current.totals.expense) - Number(previous.totals.expense)).toFixed(2)
        : null,
      balance_change: hasPreviousData
        ? (Number(current.totals.balance_change) - Number(previous.totals.balance_change)).toFixed(2)
        : null,
    },
  };
}

function getFilteredRecords() {
  const keyword = keywordFilter.value.trim().toLowerCase();

  return records.filter((record) => {
    const matchesMonth = !monthFilter.value || record.date.startsWith(monthFilter.value);
    const matchesType = !typeFilter.value || record.type === typeFilter.value;
    const matchesCategory = !categoryFilter.value || record.category === categoryFilter.value;
    const matchesKeyword = !keyword || record.note.toLowerCase().includes(keyword);

    return matchesMonth && matchesType && matchesCategory && matchesKeyword;
  });
}

function updateCategoryOptions() {
  const currentCategory = categoryFilter.value;
  const categories = [...new Set(records.map((record) => record.category))]
    .filter(Boolean)
    .sort((first, second) => first.localeCompare(second, "zh-CN"));

  categoryFilter.innerHTML = '<option value="">全部类别</option>';
  categories.forEach((category) => {
    const option = document.createElement("option");
    option.value = category;
    option.textContent = category;
    categoryFilter.append(option);
  });

  categoryFilter.value = categories.includes(currentCategory) ? currentCategory : "";
}

function updateMonthSummary() {
  const aggregate = calculateMonthAggregate(monthFilter.value);
  selectedMonthLabel.textContent = monthFilter.value ? `${monthFilter.value} 月度统计` : "全部月份统计";
  monthIncomeAmount.textContent = formatTotalMoney(Number(aggregate.totals.income));
  monthExpenseAmount.textContent = formatTotalMoney(Number(aggregate.totals.expense));
  monthBalanceAmount.textContent = formatTotalMoney(Number(aggregate.totals.balance_change));
}

function renderExpenseChart(filteredRecords) {
  const categoryTotals = {};

  filteredRecords.forEach((record) => {
    if (record.type === "支出") {
      categoryTotals[record.category] = (categoryTotals[record.category] || 0) + record.amount;
    }
  });

  const entries = Object.entries(categoryTotals).sort((first, second) => second[1] - first[1]);
  expenseChart.innerHTML = "";

  if (entries.length === 0) {
    expenseChart.innerHTML = '<p class="chart-empty">当前筛选范围内还没有支出记录。</p>';
    return;
  }

  const largestAmount = entries[0][1];
  entries.forEach(([category, amount]) => {
    const row = document.createElement("div");
    const label = document.createElement("div");
    const categoryName = document.createElement("span");
    const total = document.createElement("b");
    const track = document.createElement("div");
    const bar = document.createElement("div");

    row.className = "chart-row";
    label.className = "chart-label";
    track.className = "chart-track";
    bar.className = "chart-bar";
    categoryName.textContent = category;
    total.textContent = formatTotalMoney(amount);
    bar.style.width = `${(amount / largestAmount) * 100}%`;
    label.append(categoryName, total);
    track.append(bar);
    row.append(label, track);
    expenseChart.append(row);
  });
}

function renderMonthlyAiSummary() {
  aiMonthlySummaryText.innerHTML = "";
  aiMonthlySummaryContent.hidden = !monthlyAiSummary;

  if (!monthlyAiSummary) {
    if (!aiMonthlySummaryButton.disabled) {
      aiMonthlySummaryButton.textContent = "生成总结";
    }
    return;
  }

  const { response, generatedAt, dataKey } = monthlyAiSummary;
  const summary = response.summary;
  if (!summary) {
    return;
  }

  const entries = [
    summary.overview,
    summary.largest_category_observation,
    summary.change_observation,
    summary.neutral_observation,
    summary.suggestion,
  ].filter(Boolean);
  entries.forEach((entry) => {
    const paragraph = document.createElement("p");
    paragraph.textContent = entry;
    aiMonthlySummaryText.append(paragraph);
  });
  aiMonthlySummaryMeta.textContent = `统计范围：${response.statistics_period_start} 至 ${response.statistics_period_end}。AI 生成于：${generatedAt}。Prompt：${response.prompt_version}。`;
  aiMonthlySummaryContent.dataset.key = dataKey;
  aiMonthlySummaryButton.textContent = "重新生成";
}

function syncMonthlyAiSummary() {
  const request = buildMonthlySummaryRequest();
  const dataKey = request ? JSON.stringify(request) : null;
  if (monthlyAiSummary && monthlyAiSummary.dataKey !== dataKey) {
    monthlyAiSummary = null;
    renderMonthlyAiSummary();
  }
}

function refreshView() {
  updateCategoryOptions();
  updateSummary();
  updateMonthSummary();
  syncMonthlyAiSummary();
  renderRecords();
}

function updateSummary() {
  let totalIncome = 0;
  let totalExpense = 0;

  records.forEach((record) => {
    if (record.type === "收入") {
      totalIncome += record.amount;
    } else {
      totalExpense += record.amount;
    }
  });

  incomeAmount.textContent = formatTotalMoney(totalIncome);
  expenseAmount.textContent = formatTotalMoney(totalExpense);
  balanceAmount.textContent = formatTotalMoney(totalIncome - totalExpense);
}

function renderRecords() {
  const filteredRecords = getFilteredRecords();
  recordList.innerHTML = "";
  recordCount.textContent = `显示 ${filteredRecords.length} 条记录`;

  if (records.length === 0) {
    recordList.innerHTML = '<li class="empty-record">还没有记录，请先添加一条。</li>';
    renderExpenseChart(filteredRecords);
    return;
  }

  if (filteredRecords.length === 0) {
    recordList.innerHTML = '<li class="empty-record">没有符合当前筛选条件的记录。</li>';
    renderExpenseChart(filteredRecords);
    return;
  }

  filteredRecords.forEach((record) => {
    const index = records.indexOf(record);
    const item = document.createElement("li");
    const details = document.createElement("div");
    const title = document.createElement("strong");
    const meta = document.createElement("span");
    const side = document.createElement("div");
    const amount = document.createElement("b");
    const actions = document.createElement("div");
    const editButton = document.createElement("button");
    const deleteButton = document.createElement("button");
    const amountClass = record.type === "收入" ? "income" : "";

    title.textContent = record.note || record.category;
    meta.textContent = `${record.date} · ${record.type} · ${record.category}`;
    amount.textContent = formatMoney(record.amount, record.type);
    amount.className = amountClass;
    side.className = "record-side";
    actions.className = "record-actions";
    editButton.type = "button";
    editButton.className = "edit-button";
    editButton.textContent = "编辑";
    deleteButton.type = "button";
    deleteButton.className = "delete-button";
    deleteButton.textContent = "删除";

    editButton.addEventListener("click", () => {
      editingIndex = index;
      dateInput.value = record.date;
      typeInput.value = record.type;
      amountInput.value = record.amount;
      categoryInput.value = record.category;
      noteInput.value = record.note;
      submitButton.textContent = "保存修改";
      showMessage("正在编辑这条记录。", true);
    });

    deleteButton.addEventListener("click", async () => {
      const confirmed = confirm("确定要删除这条记录吗？");

      if (!confirmed) {
        return;
      }

      if (isCloudMode) {
        const { error } = await supabaseClient
          .from("records")
          .delete()
          .eq("id", record.id);

        if (error) {
          showMessage("删除云端记录失败，请稍后重试。");
          return;
        }
      }

      records.splice(index, 1);
      editingIndex = null;
      submitButton.textContent = "添加记录";
      recordForm.reset();
      saveLocalRecords();
      showMessage("记录已删除。", true);
      refreshView();
    });

    details.append(title, meta);
    actions.append(editButton, deleteButton);
    side.append(amount, actions);
    item.append(details, side);
    recordList.prepend(item);
  });

  renderExpenseChart(filteredRecords);
}

function escapeCsvValue(value) {
  return `"${String(value ?? "").replaceAll('"', '""')}"`;
}

function exportRecords() {
  if (isCloudMode && !cloudRecordsReady) {
    showMessage("云端账单尚未读取完成，请稍后再导出。");
    return;
  }

  const filteredRecords = getFilteredRecords();
  if (filteredRecords.length === 0) {
    showMessage("当前没有可导出的记录。");
    return;
  }

  const rows = [
    ["日期", "类型", "金额", "类别", "备注"],
    ...filteredRecords.map((record) => [record.date, record.type, record.amount.toFixed(2), record.category, record.note]),
  ];
  const csv = `\uFEFF${rows.map((row) => row.map(escapeCsvValue).join(",")).join("\n")}`;
  const file = new Blob([csv], { type: "text/csv;charset=utf-8" });
  const downloadUrl = URL.createObjectURL(file);
  const link = document.createElement("a");

  link.href = downloadUrl;
  link.download = `u-money-${monthFilter.value || "全部记录"}.csv`;
  document.body.append(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(downloadUrl);
  showMessage(`已导出 ${filteredRecords.length} 条记录。`, true);
}

function formatAiCandidateStatus(candidate) {
  const requiredFields = [
    ["date", "日期"],
    ["type", "类型"],
    ["amount", "金额"],
    ["category", "类别"],
  ];
  const missing = requiredFields
    .filter(([field]) => !candidate[field])
    .map(([, label]) => label);

  if (missing.length > 0) {
    return `还需要补充：${missing.join("、")}。`;
  }

  if ((candidate.uncertain_fields || []).length > 0) {
    return "AI 对这条记录存在不确定性，请仔细确认。";
  }

  return "请确认这条 AI 草稿是否正确。";
}

function renderAiCandidates() {
  aiCandidateList.innerHTML = "";
  aiCandidateArea.hidden = aiCandidates.length === 0;

  aiCandidates.forEach((candidate, index) => {
    const item = document.createElement("li");
    const heading = document.createElement("div");
    const title = document.createElement("strong");
    const removeButton = document.createElement("button");
    const fields = document.createElement("div");
    const status = document.createElement("p");
    const controls = [
      ["日期", "date", "date"],
      ["类型", "type", "select"],
      ["金额", "amount", "number"],
      ["类别", "category", "text"],
      ["备注", "note", "text"],
    ];

    item.className = "ai-candidate-item";
    heading.className = "ai-candidate-heading";
    fields.className = "ai-candidate-grid";
    status.className = "ai-candidate-status";
    title.textContent = `候选记录 ${index + 1}`;
    removeButton.type = "button";
    removeButton.className = "delete-button";
    removeButton.textContent = "删除候选";
    removeButton.addEventListener("click", () => {
      aiCandidates = aiCandidates.filter((itemCandidate) => itemCandidate.candidate_id !== candidate.candidate_id);
      renderAiCandidates();
      showAiMessage(aiCandidates.length ? "已删除一条候选记录。" : "已清空全部候选记录。", true);
    });

    controls.forEach(([labelText, field, controlType]) => {
      const label = document.createElement("label");
      const labelName = document.createElement("span");
      let control;

      labelName.textContent = labelText;
      if (controlType === "select") {
        control = document.createElement("select");
        ["", "支出", "收入"].forEach((value) => {
          const option = document.createElement("option");
          option.value = value;
          option.textContent = value || "请选择";
          control.append(option);
        });
      } else {
        control = document.createElement("input");
        control.type = controlType;
        if (controlType === "number") {
          control.min = "0.01";
          control.step = "0.01";
          control.inputMode = "decimal";
        }
      }

      control.value = candidate[field] || "";
      control.addEventListener("input", () => {
        candidate[field] = control.value;
        status.textContent = formatAiCandidateStatus(candidate);
      });
      control.addEventListener("change", () => {
        candidate[field] = control.value;
        status.textContent = formatAiCandidateStatus(candidate);
      });
      label.append(labelName, control);
      fields.append(label);
    });

    status.textContent = formatAiCandidateStatus(candidate);
    heading.append(title, removeButton);
    item.append(heading, fields, status);
    aiCandidateList.append(item);
  });
}

async function getAiAccessToken() {
  if (!supabaseClient || !currentUser) {
    return null;
  }

  const { data, error } = await supabaseClient.auth.getSession();
  if (error || !data.session?.access_token) {
    return null;
  }

  return data.session.access_token;
}

async function generateMonthlyAiSummary() {
  const requestBody = buildMonthlySummaryRequest();

  if (!aiEnabled) {
    showMonthlySummaryMessage("AI 月度总结已关闭，普通月度统计仍可使用。");
    return;
  }
  if (!aiServiceUrl) {
    showMonthlySummaryMessage("智能服务尚未配置，普通月度统计仍可使用。");
    return;
  }
  if (!requestBody) {
    showMonthlySummaryMessage("请先在筛选区域选择一个月份。");
    return;
  }
  if (requestBody.totals.record_count === 0) {
    monthlyAiSummary = null;
    renderMonthlyAiSummary();
    showMonthlySummaryMessage("这个月还没有记录，普通统计仍可使用。");
    return;
  }

  const accessToken = await getAiAccessToken();
  if (!accessToken) {
    showMonthlySummaryMessage("请先登录后再生成 AI 月度总结。");
    return;
  }

  aiMonthlySummaryButton.disabled = true;
  aiMonthlySummaryButton.textContent = "正在生成...";
  showMonthlySummaryMessage("AI 正在根据月度汇总生成文字总结...", true);

  try {
    const response = await fetch(`${aiServiceUrl}/ai/monthly-summary`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${accessToken}`,
      },
      body: JSON.stringify(requestBody),
    });
    const payload = await response.json();

    if (!response.ok) {
      showMonthlySummaryMessage(payload.error?.message || "AI 总结暂时不可用，普通统计仍可使用。");
      return;
    }
    if (payload.data_status === "empty" || !payload.summary) {
      monthlyAiSummary = null;
      renderMonthlyAiSummary();
      showMonthlySummaryMessage(payload.warnings?.[0] || "这个月还没有记录。", true);
      return;
    }

    monthlyAiSummary = {
      response: payload,
      generatedAt: new Date().toLocaleString("zh-CN", { hour12: false }),
      dataKey: JSON.stringify(requestBody),
    };
    renderMonthlyAiSummary();
    showMonthlySummaryMessage("AI 总结已生成。普通统计数据由页面代码计算。", true);
  } catch (error) {
    showMonthlySummaryMessage("无法连接智能服务，普通月度统计仍可使用。");
  } finally {
    aiMonthlySummaryButton.disabled = !aiEnabled || !aiServiceUrl;
    if (!aiMonthlySummaryButton.disabled && !monthlyAiSummary) {
      aiMonthlySummaryButton.textContent = "生成总结";
    }
  }
}

async function parseAiTransactions(event) {
  event.preventDefault();
  const text = aiTextInput.value.trim();

  if (!aiEnabled) {
    showAiMessage("AI 辅助已关闭，请使用普通手动记账。");
    return;
  }
  if (!aiServiceUrl) {
    showAiMessage("智能服务尚未配置，仍可使用普通手动记账。");
    return;
  }
  if (!text) {
    showAiMessage("请输入一条记账描述。");
    return;
  }
  if (text.length > 1000) {
    showAiMessage("内容太长，请分成几次记录。");
    return;
  }

  const accessToken = await getAiAccessToken();
  if (!accessToken) {
    showAiMessage("请先登录后再使用智能记账。");
    return;
  }

  aiParseButton.disabled = true;
  aiParseButton.textContent = "正在识别...";
  showAiMessage("AI 正在识别，请稍候...", true);

  try {
    const response = await fetch(`${aiServiceUrl}/ai/parse-transactions`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${accessToken}`,
      },
      body: JSON.stringify({
        text,
        reference_date: getLocalDateString(),
        timezone: "Asia/Shanghai",
        currency: "CNY",
      }),
    });
    const payload = await response.json();

    if (!response.ok) {
      showAiMessage(payload.error?.message || "智能解析暂时不可用，请手动记账。");
      return;
    }
    if (payload.status === "rejected") {
      aiCandidates = [];
      renderAiCandidates();
      showAiMessage(payload.warnings?.[0] || "没有识别到可用的记账内容。");
      return;
    }

    aiCandidates = payload.transactions.map((candidate) => ({
      ...candidate,
      date: candidate.date || "",
      type: candidate.type || "",
      amount: candidate.amount || "",
      category: candidate.category || "",
      note: candidate.note || "",
    }));
    renderAiCandidates();
    showAiMessage(
      payload.needs_confirmation
        ? "识别完成，但有字段需要你补充或确认。"
        : "识别完成，请检查候选记录后再保存。",
      true,
    );
  } catch (error) {
    showAiMessage("无法连接智能服务，仍可使用普通手动记账。");
  } finally {
    aiParseButton.disabled = false;
    aiParseButton.textContent = "开始识别";
  }
}

async function saveAiCandidates() {
  if (!isCloudMode || !currentUser || !supabaseClient) {
    showAiMessage("请先登录后再保存智能记账结果。");
    return;
  }
  if (aiCandidates.length === 0) {
    showAiMessage("没有可保存的候选记录。");
    return;
  }

  const recordsToSave = aiCandidates.map((candidate) => ({
    date: candidate.date,
    type: candidate.type,
    amount: Number(candidate.amount),
    category: candidate.category.trim(),
    note: candidate.note.trim(),
    user_id: currentUser.id,
  }));
  const invalidRecord = recordsToSave.find((record) => (
    !record.date
    || !["收入", "支出"].includes(record.type)
    || !Number.isFinite(record.amount)
    || record.amount <= 0
    || !record.category
  ));

  if (invalidRecord) {
    showAiMessage("请先补齐每条候选记录的日期、类型、金额和类别。");
    return;
  }

  confirmAiCandidatesButton.disabled = true;
  confirmAiCandidatesButton.textContent = "正在保存...";
  const { error } = await supabaseClient.from("records").insert(recordsToSave);
  confirmAiCandidatesButton.disabled = false;
  confirmAiCandidatesButton.textContent = "确认并保存";

  if (error) {
    showAiMessage("保存候选记录失败，请稍后重试。");
    return;
  }

  aiCandidates = [];
  aiTextInput.value = "";
  renderAiCandidates();
  showAiMessage(`已保存 ${recordsToSave.length} 条确认后的记录。`, true);
  await loadCloudRecords();
}

recordForm.addEventListener("submit", async (event) => {
  event.preventDefault();

  const date = dateInput.value;
  const type = typeInput.value;
  const amount = Number(amountInput.value);
  const category = categoryInput.value.trim();
  const note = noteInput.value.trim();

  if (!date) {
    showMessage("请选择日期。");
    return;
  }

  if (!amount || amount <= 0) {
    showMessage("请输入大于 0 的金额。");
    return;
  }

  if (!category) {
    showMessage("请输入类别。");
    return;
  }

  const record = {
    date,
    type,
    amount,
    category,
    note,
  };

  if (isCloudMode) {
    if (editingIndex === null) {
      const { data, error } = await supabaseClient
        .from("records")
        .insert({
          ...record,
          user_id: currentUser.id,
        })
        .select("id, date, type, amount, category, note")
        .single();

      if (error) {
        showMessage("添加云端记录失败，请稍后重试。");
        return;
      }

      records.push(normalizeCloudRecord(data));
      showMessage("记录已添加到云端。", true);
    } else {
      const recordId = records[editingIndex].id;
      const { data, error } = await supabaseClient
        .from("records")
        .update(record)
        .eq("id", recordId)
        .select("id, date, type, amount, category, note")
        .single();

      if (error) {
        showMessage("修改云端记录失败，请稍后重试。");
        return;
      }

      records[editingIndex] = normalizeCloudRecord(data);
      editingIndex = null;
      submitButton.textContent = "添加记录";
      showMessage("云端记录已修改。", true);
    }
  } else if (editingIndex === null) {
    records.push(record);
    showMessage("记录已添加到本地浏览器。", true);
  } else {
    records[editingIndex] = record;
    editingIndex = null;
    submitButton.textContent = "添加记录";
    showMessage("本地记录已修改。", true);
  }

  recordForm.reset();
  saveLocalRecords();
  refreshView();
});

[monthFilter, typeFilter, categoryFilter, keywordFilter].forEach((filter) => {
  filter.addEventListener("input", refreshView);
  filter.addEventListener("change", refreshView);
});

clearFiltersButton.addEventListener("click", () => {
  monthFilter.value = "";
  typeFilter.value = "";
  categoryFilter.value = "";
  keywordFilter.value = "";
  refreshView();
});

exportButton.addEventListener("click", exportRecords);

aiEnabledToggle.addEventListener("change", () => {
  aiEnabled = aiEnabledToggle.checked;
  localStorage.setItem(aiPreferenceKey, String(aiEnabled));
  updateAiAvailability();
});

aiParseForm.addEventListener("submit", parseAiTransactions);
aiMonthlySummaryButton.addEventListener("click", generateMonthlyAiSummary);
confirmAiCandidatesButton.addEventListener("click", saveAiCandidates);
cancelAiCandidatesButton.addEventListener("click", () => {
  aiCandidates = [];
  renderAiCandidates();
  showAiMessage("已取消全部 AI 候选记录。", true);
});

signUpButton.addEventListener("click", async () => {
  if (!supabaseClient) {
    showAuthMessage("Supabase 暂时无法连接，请检查网络后重试。");
    return;
  }

  const email = emailInput.value.trim();
  const password = passwordInput.value;

  if (!email || !password) {
    showAuthMessage("请输入邮箱和密码。");
    return;
  }

  const { data, error } = await supabaseClient.auth.signUp({
    email,
    password,
  });
  passwordInput.value = "";

  if (error) {
    showAuthMessage("注册失败，请检查邮箱格式或稍后重试。");
    return;
  }

  updateAuthView(data.session?.user || null);
  showAuthMessage("注册已提交。如果 Supabase 要求邮箱确认，请先去邮箱点击确认链接。", true);
  if (data.session?.user) {
    await loadCloudRecords();
  }
});

signInButton.addEventListener("click", async () => {
  if (!supabaseClient) {
    showAuthMessage("Supabase 暂时无法连接，请检查网络后重试。");
    return;
  }

  const email = emailInput.value.trim();
  const password = passwordInput.value;

  if (!email || !password) {
    showAuthMessage("请输入邮箱和密码。");
    return;
  }

  const { data, error } = await supabaseClient.auth.signInWithPassword({
    email,
    password,
  });
  passwordInput.value = "";

  if (error) {
    showAuthMessage("登录失败，请检查邮箱和密码后再试。");
    return;
  }

  updateAuthView(data.user);
  showAuthMessage("登录成功。", true);
  await loadCloudRecords();
});

signOutButton.addEventListener("click", async () => {
  if (!supabaseClient) {
    showAuthMessage("Supabase 暂时无法连接，请检查网络后重试。");
    return;
  }

  const { error } = await supabaseClient.auth.signOut();

  if (error) {
    showAuthMessage("退出登录失败，请稍后重试。");
    return;
  }

  emailInput.value = "";
  passwordInput.value = "";
  updateAuthView(null);
  loadLocalRecords();
  showAuthMessage("已退出登录。", true);
});

if (supabaseClient) {
  supabaseClient.auth.onAuthStateChange(async (event, session) => {
    updateAuthView(session?.user || null);

    if (session?.user) {
      await loadCloudRecords();
    } else {
      loadLocalRecords();
    }
  });

  supabaseClient.auth.getUser().then(async ({ data }) => {
    updateAuthView(data.user);
    if (data.user) {
      await loadCloudRecords();
    }
  });
} else {
  showAuthMessage("Supabase 暂时无法连接，请检查网络后重试。");
  updateAuthView(null);
}

loadLocalRecords();
updateAiAvailability();
