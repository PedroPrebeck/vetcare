/** Primitivas visuais. Todo texto vindo do banco passa por escapeHTML. */
export const escapeHTML = (value) =>
  String(value ?? "").replace(
    /[&<>"']/g,
    (char) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[
        char
      ],
  );
export const money = (cents) =>
  new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" }).format(
    cents / 100,
  );
export const dateLabel = (value) =>
  value
    ? new Date(value.slice(0, 10) + "T12:00:00").toLocaleDateString("pt-BR")
    : "Não informado";
export const longDate = (value) =>
  new Date(value + "T12:00:00").toLocaleDateString("pt-BR", {
    weekday: "long",
    day: "numeric",
    month: "long",
    year: "numeric",
  });
const paths = {
  home: '<path d="m3 10 9-7 9 7v10H3z"/><path d="M9 20v-8h6v8"/>',
  calendar:
    '<rect x="3" y="5" width="18" height="16" rx="2"/><path d="M16 3v4M8 3v4M3 11h18m-12 5h3"/>',
  paw: '<ellipse cx="7" cy="7" rx="2" ry="3"/><ellipse cx="17" cy="7" rx="2" ry="3"/><ellipse cx="3" cy="12" rx="1.5" ry="2"/><ellipse cx="21" cy="12" rx="1.5" ry="2"/><path d="M7 20c-4-1 0-8 5-8s9 7 5 8c-2 0-3-1-5-1s-3 1-5 1z"/>',
  users:
    '<circle cx="9" cy="7" r="3"/><path d="M2 21v-3a7 7 0 0 1 14 0v3m1-17a3 3 0 0 1 0 6m2 4a5 5 0 0 1 3 5v2"/>',
  stethoscope:
    '<path d="M5 3v6a5 5 0 0 0 10 0V3M3 3h4m6 0h4m-7 11v3a5 5 0 0 0 10 0v-3"/><circle cx="20" cy="12" r="2"/>',
  file: '<rect x="5" y="3" width="14" height="18" rx="2"/><path d="M9 8h6m-6 4h6m-6 4h3"/>',
  chart: '<path d="M5 21V12m7 9V7m7 14V3"/>',
  plus: '<path d="M12 5v14M5 12h14"/>',
  edit: '<path d="m16 3 5 5-12 12-6 1 1-6zM14 5l5 5"/>',
  eye: '<path d="M2 12s4-7 10-7 10 7 10 7-4 7-10 7S2 12 2 12z"/><circle cx="12" cy="12" r="3"/>',
  archive: '<path d="M4 7h16v14H4zM3 3h18v4H3m6 5h6"/>',
  close: '<path d="m6 6 12 12M6 18 18 6"/>',
  check: '<path d="m4 12 5 5L20 6"/>',
  wallet: '<path d="M20 7H4V4h15M4 7v14h17V7z"/><path d="M16 12h5v5h-5z"/>',
  book: '<path d="M12 5c-4-3-9-2-9-2v16s5-1 9 2c4-3 9-2 9-2V3s-5-1-9 2zm0 0v16"/>',
};
export const icon = (name) =>
  `<svg viewBox="0 0 24 24" aria-hidden="true">${paths[name] || paths.file}</svg>`;
export function button(label, action, options = {}) {
  return `<button type="button" class="btn ${options.style || ""}" data-action="${action}" ${options.id ? `data-id="${options.id}"` : ""} ${options.table ? `data-table="${options.table}"` : ""}>${options.icon ? icon(options.icon) : ""}${escapeHTML(label)}</button>`;
}
export function iconButton(label, action, id, table, shape) {
  return `<button type="button" class="btn icon" title="${escapeHTML(label)}" aria-label="${escapeHTML(label)}" data-action="${action}" data-id="${id}" ${table ? `data-table="${table}"` : ""}>${icon(shape)}</button>`;
}
export const badge = (status) =>
  `<span class="badge ${{ Confirmado: "confirmed", Concluído: "done", Cancelado: "cancelled", Arquivado: "archived" }[status] || ""}">${escapeHTML(status)}</span>`;
export const avatar = (name, id) =>
  `<span class="avatar c${id % 6}">${escapeHTML(name.slice(0, 1).toUpperCase())}</span>`;
export const animal = (pet) =>
  `<div class="animal">${avatar(pet.pet_name || pet.name, pet.pet_id || pet.id)}<div><span class="name">${escapeHTML(pet.pet_name || pet.name)}</span><span class="meta">${escapeHTML(pet.species)}${pet.breed ? " · " + escapeHTML(pet.breed) : ""}</span></div></div>`;
export function table(headers, body, empty = "Nenhum registro encontrado.") {
  return `<div class="table-wrap"><table><thead><tr>${headers.map((h) => `<th scope="col">${h}</th>`).join("")}</tr></thead><tbody>${body || `<tr><td colspan="${headers.length}"><div class="empty">${empty}</div></td></tr>`}</tbody></table></div>`;
}
export function panel(title, body, action = "") {
  return `<section class="panel"><div class="panel-head"><h2>${escapeHTML(title)}</h2>${action}</div>${body}</section>`;
}
export function toast(message) {
  const element = document.querySelector("#toast");
  element.textContent = message;
  element.classList.add("visible");
  clearTimeout(toast.timer);
  toast.timer = setTimeout(() => element.classList.remove("visible"), 4000);
}
export function showModal(title, body, actions = "") {
  const modal = document.querySelector("#modal");
  document.querySelector("#modal-content").innerHTML =
    `<div class="modal-head"><h2 id="modal-title">${escapeHTML(title)}</h2>${button("", "close-modal", { icon: "close" })}</div>${body}${actions}`;
  modal
    .querySelector('[data-action="close-modal"]')
    .setAttribute("aria-label", "Fechar janela");
  if (!modal.open) modal.showModal();
  const focus =
    modal.querySelector("[autofocus]") ||
    modal.querySelector("input,select,textarea");
  focus?.focus();
}
