/** Composição das telas, navegação por hash e comandos da interface. */
import { request } from "./client.js";
import {
  pages,
  overview,
  agenda,
  master,
  finance,
  documentation,
} from "./views.js";
import {
  updateCompanionOptions,
  masterForm,
  appointmentForm,
  recordForm,
  paymentForm,
} from "./forms.js";
import {
  escapeHTML as e,
  icon,
  button,
  badge,
  animal,
  showModal,
  toast,
  money,
  dateLabel,
  longDate,
} from "./ui.js";
let data = null;
const state = {
  query: "",
  agendaDate: "",
  status: "",
  archived: false,
  financeTab: "balances",
};
const page = () =>
  Object.hasOwn(pages, location.hash.slice(1))
    ? location.hash.slice(1)
    : "overview";
const modal = document.querySelector("#modal");

async function refresh() {
  data = await request("/bootstrap");
  if (!state.agendaDate && state.agendaDate !== null)
    state.agendaDate = data.dashboard.today;
  render();
}
function render() {
  const current = page(),
    focus = document.activeElement?.id,
    selection = document.activeElement?.selectionStart;
  document.querySelector("#navigation").innerHTML = Object.entries(pages)
    .filter(([key]) => key !== "documentation")
    .map(
      ([key, [label, shape]]) =>
        `<a href="#${key}" class="${current === key ? "active" : ""}" ${current === key ? 'aria-current="page"' : ""}>${icon(shape)}${label}</a>`,
    )
    .join("");
  document.querySelector("#page-title").textContent = pages[current][0];
  const subtitles = {
    overview: longDate(data.dashboard.today),
    agenda: "Agendamentos e atendimentos da clínica",
    pets: "Cadastro e histórico de cada animal",
    tutors: "Responsáveis pelos pacientes",
    veterinarians: "Equipe e especialidades",
    services: "Catálogo de serviços e valores",
    finance: "Recebimentos e saldos das consultas",
    documentation: "Modelagem, scripts e roteiro de apresentação",
  };
  document.querySelector("#page-subtitle").textContent = subtitles[current];
  const labels = {
    pets: "Novo paciente",
    tutors: "Novo tutor",
    veterinarians: "Novo veterinário",
    services: "Novo serviço",
  };
  document.querySelector("#page-action").innerHTML = [
    "overview",
    "agenda",
  ].includes(current)
    ? button("Novo agendamento", "new-appointment", {
        style: "primary",
        icon: "plus",
      })
    : labels[current]
      ? button(labels[current], "new-master", {
          style: "primary",
          icon: "plus",
          table: current,
        })
      : "";
  const content = document.querySelector("#content");
  content.innerHTML =
    current === "overview"
      ? overview(data)
      : current === "agenda"
        ? agenda(data, state)
        : current === "finance"
          ? finance(data, state)
          : current === "documentation"
            ? documentation()
            : master(data, state, current);
  content.setAttribute("aria-busy", "false");
  if (focus === "search") {
    const search = document.querySelector("#search");
    search?.focus();
    search?.setSelectionRange(selection, selection);
  }
}
window.addEventListener("hashchange", () => {
  state.query = "";
  state.archived = false;
  render();
  document.querySelector("#main").focus();
});
document.addEventListener("input", (event) => {
  if (event.target.id === "search") {
    state.query = event.target.value;
    render();
  }
});
document.addEventListener("change", (event) => {
  if (event.target.id === "field-pet_id") {
    updateCompanionOptions(data, event.target.value);
    return;
  }
  if (event.target.id === "agenda-date")
    state.agendaDate = event.target.value || null;
  else if (event.target.id === "status-filter")
    state.status = event.target.value;
  else if (event.target.id === "archived-filter")
    state.archived = event.target.checked;
  else return;
  render();
});

async function history(id) {
  const pet = data.pets.find((p) => p.id === id),
    result = await request(`/pets/${id}/history`);
  showModal(
    `Histórico de ${pet.name}`,
    `<div class="modal-body"><div class="patient-head">${animal(pet)}${badge(pet.active ? "Ativo" : "Arquivado")}</div><div class="patient-details"><div><span>Tutores</span>${e(pet.tutor_name)}</div><div><span>Nascimento</span>${dateLabel(pet.birth_date)}</div><div><span>Sexo</span>${e(pet.sex)}</div><div><span>Peso atual</span>${pet.weight_kg ?? "Não informado"}${pet.weight_kg ? " kg" : ""}</div></div>${pet.notes ? `<p>${e(pet.notes)}</p>` : ""}<h3>Prontuários</h3>${result.records.map((r) => `<article class="record"><h3>${dateLabel(r.starts_at)} · ${e(r.service_name)}</h3><span class="meta">${e(r.veterinarian_name)} · Acompanhante: ${e(r.tutor_name || "Não registrado")}${r.weight_kg ? " · " + r.weight_kg + " kg" : ""}</span><span class="record-label">Queixa</span><p>${e(r.complaint)}</p><span class="record-label">Avaliação</span><p>${e(r.diagnosis)}</p><span class="record-label">Conduta</span><p>${e(r.treatment || "Não informada")}</p></article>`).join("") || '<p class="muted">Nenhum prontuário registrado.</p>'}<h3>Consultas</h3><div class="history-list">${result.appointments.map((a) => `<div class="history-row"><span>${dateLabel(a.starts_at)} · ${a.starts_at.slice(11)}<span class="meta">${e(a.service_name)} · Acompanhante: ${e(a.tutor_name || "Não registrado")}</span></span>${badge(a.status)}</div>`).join("") || '<p class="muted">Nenhuma consulta registrada.</p>'}</div></div>`,
  );
}
function appointmentDetail(id) {
  const a = data.appointments.find((x) => x.id === id),
    open = ["Agendado", "Confirmado"].includes(a.status);
  const controls = `${button("Histórico do paciente", "history", { id: a.pet_id, icon: "eye" })}${open && a.status === "Agendado" ? button("Confirmar", "confirm-appointment", { id, icon: "check" }) : ""}${open ? button("Cancelar consulta", "cancel-appointment", { id, style: "danger" }) : ""}${a.status !== "Cancelado" && a.balance_cents > 0 ? button("Receber", "payment", { id, icon: "wallet" }) : ""}${open ? button("Atender", "record", { id, style: "primary", icon: "stethoscope" }) : ""}`;
  showModal(
    "Consulta de " + a.pet_name,
    `<div class="modal-body"><div class="patient-head">${animal(a)}${badge(a.status)}</div><div class="patient-details"><div><span>Data e horário</span>${dateLabel(a.starts_at)} · ${a.starts_at.slice(11)}</div><div><span>Duração</span>${a.duration_minutes} min</div><div><span>Acompanhante</span>${e(a.tutor_name || "Acompanhante não registrado")}</div><div><span>Telefone</span>${e(a.tutor_phone)}</div><div><span>Veterinário</span>${e(a.veterinarian_name)}</div><div><span>Serviço</span>${e(a.service_name)}</div><div><span>Valor</span>${money(a.fee_cents)}</div><div><span>Saldo</span>${money(a.balance_cents)}</div></div>${a.notes ? `<p>${e(a.notes)}</p>` : ""}<p class="form-error" role="alert"></p></div>`,
    `<div class="modal-actions actions-wrap">${controls}</div>`,
  );
}
function confirmDialog(title, message, action, id, table = null) {
  showModal(
    title,
    `<div class="modal-body"><p>${e(message)}</p><p class="form-error" role="alert"></p></div>`,
    `<div class="modal-actions">${button("Voltar", "close-modal")}${button("Confirmar", action, { id, table, style: "primary" })}</div>`,
  );
}
document.addEventListener("click", async (event) => {
  const target = event.target.closest("[data-action]");
  if (!target || target.disabled || !data) return;
  const action = target.dataset.action,
    id = Number(target.dataset.id),
    table = target.dataset.table;
  try {
    switch (action) {
      case "close-modal":
        modal.close();
        break;
      case "new-master":
        masterForm(table, data);
        break;
      case "edit-master":
        masterForm(
          table,
          data,
          data[table].find((r) => r.id === id),
        );
        break;
      case "new-appointment":
        appointmentForm(
          data,
          null,
          page() === "agenda" ? state.agendaDate : null,
        );
        break;
      case "edit-appointment":
        appointmentForm(
          data,
          data.appointments.find((a) => a.id === id),
        );
        break;
      case "appointment-detail":
        appointmentDetail(id);
        break;
      case "history":
        await history(id);
        break;
      case "record":
        recordForm(
          data,
          data.appointments.find((a) => a.id === id),
        );
        break;
      case "payment":
        paymentForm(
          data,
          data.appointments.find((a) => a.id === id),
        );
        break;
      case "all-dates":
        state.agendaDate = null;
        render();
        break;
      case "finance-tab":
        state.financeTab = target.dataset.tab;
        render();
        break;
      case "archive-master": {
        const r = data[table].find((x) => x.id === id);
        confirmDialog(
          r.active ? "Arquivar cadastro" : "Reativar cadastro",
          `${r.name}: ${r.active ? "o histórico será preservado e o cadastro sairá das opções de novos agendamentos." : "o cadastro voltará a ficar disponível."}`,
          "do-archive",
          id,
          table,
        );
        break;
      }
      case "do-archive": {
        target.disabled = true;
        await request(`/${table}/${id}`, "PATCH", {
          active: data[table].find((r) => r.id === id).active ? 0 : 1,
        });
        modal.close();
        await refresh();
        toast("Cadastro atualizado.");
        break;
      }
      case "cancel-appointment":
        confirmDialog(
          "Cancelar consulta",
          "A consulta continuará no histórico com o status Cancelado. Consultas com recebimentos não podem ser canceladas.",
          "do-cancel",
          id,
        );
        break;
      case "do-cancel":
      case "confirm-appointment":
        target.disabled = true;
        await request(`/appointments/${id}`, "PATCH", {
          status: action === "do-cancel" ? "Cancelado" : "Confirmado",
        });
        modal.close();
        await refresh();
        toast("Consulta atualizada.");
        break;
    }
  } catch (error) {
    const box = modal.open ? modal.querySelector(".form-error") : null;
    if (box) {
      box.textContent = error.message;
      box.focus();
    } else toast(error.message);
    target.disabled = false;
  }
});
document.addEventListener("submit", async (event) => {
  if (event.target.id !== "data-form") return;
  event.preventDefault();
  const form = event.target,
    submit = form.querySelector("[type=submit]"),
    errorBox = form.querySelector(".form-error");
  submit.disabled = true;
  errorBox.textContent = "";
  const formData = new FormData(form);
  const body = Object.fromEntries(formData);
  if (form.querySelector("[name=tutor_ids]")) body.tutor_ids = formData.getAll("tutor_ids");
  try {
    await request(form.dataset.endpoint, form.dataset.method, body);
    modal.close();
    await refresh();
    toast("Registro salvo.");
  } catch (error) {
    errorBox.textContent = error.message;
    errorBox.setAttribute("tabindex", "-1");
    errorBox.focus();
    submit.disabled = false;
  }
});
modal.addEventListener("click", (event) => {
  if (event.target === modal) {
    const bounds = modal.getBoundingClientRect();
    if (
      event.clientX < bounds.left ||
      event.clientX > bounds.right ||
      event.clientY < bounds.top ||
      event.clientY > bounds.bottom
    )
      modal.close();
  }
});
refresh().catch((error) => {
  const content = document.querySelector("#content");
  content.innerHTML = `<div class="panel empty"><strong>Não foi possível carregar os dados</strong>${e(error.message)}<p>Inicialize o banco conforme o README e recarregue a página.</p></div>`;
  content.setAttribute("aria-busy", "false");
});
