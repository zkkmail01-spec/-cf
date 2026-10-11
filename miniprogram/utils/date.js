function two(value) {
  return String(value).padStart(2, '0');
}

function formatLocalDate(value = new Date()) {
  return `${value.getFullYear()}-${two(value.getMonth() + 1)}-${two(value.getDate())}`;
}

function formatLocalMonth(value = new Date()) {
  return `${value.getFullYear()}-${two(value.getMonth() + 1)}`;
}

function shiftMonth(month, delta) {
  const [year, monthNumber] = month.split('-').map(Number);
  const date = new Date(year, monthNumber - 1 + delta, 1);
  return formatLocalMonth(date);
}

function shiftDate(value, delta) {
  const date = new Date(`${value}T00:00:00`);
  date.setDate(date.getDate() + delta);
  return formatLocalDate(date);
}

module.exports = { formatLocalDate, formatLocalMonth, shiftMonth, shiftDate };
