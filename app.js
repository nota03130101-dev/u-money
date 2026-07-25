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

const storageKey = "uMoneyRecords";
const supabaseUrl = "https://bgdphvfukmpyyiiylwcu.supabase.co";
const supabaseKey = "sb_publishable__CKu_wgZzkruoKgrUywMPA_QuZHdgNr";
const supabaseClient = window.supabase
  ? window.supabase.createClient(supabaseUrl, supabaseKey)
  : null;
let records = [];
let editingIndex = null;
let currentUser = null;
let isCloudMode = false;

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

function updateAuthView(user) {
  const isLoggedIn = Boolean(user);
  currentUser = user || null;
  isCloudMode = isLoggedIn && Boolean(supabaseClient);

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
    showMessage(`读取云端账单失败：${error.message}`);
    return;
  }

  records = data.map(normalizeCloudRecord);
  editingIndex = null;
  submitButton.textContent = "添加记录";
  recordForm.reset();
  renderRecords();
  updateSummary();
  showMessage("云端账单已同步。", true);
}

function loadLocalRecords() {
  loadRecords();
  editingIndex = null;
  submitButton.textContent = "添加记录";
  recordForm.reset();
  renderRecords();
  updateSummary();
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
  recordList.innerHTML = "";

  if (records.length === 0) {
    recordList.innerHTML = '<li class="empty-record">还没有记录，请先添加一条。</li>';
    return;
  }

  records.forEach((record, index) => {
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
          showMessage(`删除云端记录失败：${error.message}`);
          return;
        }
      }

      records.splice(index, 1);
      editingIndex = null;
      submitButton.textContent = "添加记录";
      recordForm.reset();
      saveLocalRecords();
      showMessage("记录已删除。", true);
      renderRecords();
      updateSummary();
    });

    details.append(title, meta);
    actions.append(editButton, deleteButton);
    side.append(amount, actions);
    item.append(details, side);
    recordList.prepend(item);
  });
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
        showMessage(`添加云端记录失败：${error.message}`);
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
        showMessage(`修改云端记录失败：${error.message}`);
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
  renderRecords();
  updateSummary();
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
    showAuthMessage(error.message);
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
    showAuthMessage(error.message);
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
    showAuthMessage(error.message);
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
