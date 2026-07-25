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

const storageKey = "uMoneyRecords";
let records = [];
let editingIndex = null;

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

function saveRecords() {
  localStorage.setItem(storageKey, JSON.stringify(records));
}

function loadRecords() {
  const savedRecords = localStorage.getItem(storageKey);

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

    deleteButton.addEventListener("click", () => {
      const confirmed = confirm("确定要删除这条记录吗？");

      if (!confirmed) {
        return;
      }

      records.splice(index, 1);
      editingIndex = null;
      submitButton.textContent = "添加记录";
      recordForm.reset();
      saveRecords();
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

recordForm.addEventListener("submit", (event) => {
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

  if (editingIndex === null) {
    records.push(record);
    showMessage("记录已添加。", true);
  } else {
    records[editingIndex] = record;
    editingIndex = null;
    submitButton.textContent = "添加记录";
    showMessage("记录已修改。", true);
  }

  recordForm.reset();
  saveRecords();
  renderRecords();
  updateSummary();
});

loadRecords();
renderRecords();
updateSummary();
