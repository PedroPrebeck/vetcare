/** Telas construídas a partir do estado devolvido pela API. */
import {
  escapeHTML as e,
  money,
  dateLabel,
  icon,
  button,
  iconButton,
  badge,
  animal,
  table,
  panel,
  avatar,
} from "./ui.js";
export const pages = {
  overview: ["Visão geral", "home"],
  agenda: ["Agenda", "calendar"],
  pets: ["Pacientes", "paw"],
  tutors: ["Tutores", "users"],
  veterinarians: ["Veterinários", "stethoscope"],
  services: ["Serviços", "file"],
  finance: ["Financeiro", "chart"],
  documentation: ["Documentação", "book"],
};
const match = (row, query) =>
  !query ||
  Object.values(row).some((v) =>
    String(v ?? "")
      .toLocaleLowerCase("pt-BR")
      .includes(query.toLocaleLowerCase("pt-BR")),
  );
const metric = (label, value, shape, note = "") =>
  `<div class="metric"><span class="metric-icon">${icon(shape)}</span><div><span class="metric-label">${e(label)}</span><strong class="metric-value number">${e(value)}</strong>${note ? `<span class="metric-note">${e(note)}</span>` : ""}</div></div>`;
function appointmentRows(items, full = false) {
  return items
    .map(
      (a) =>
        `<tr><td class="number">${full ? `${dateLabel(a.starts_at)}<span class="meta">${a.starts_at.slice(11)} · ${a.duration_minutes} min</span>` : a.starts_at.slice(11)}</td><td>${animal(a)}</td><td>${e(a.tutor_name)}</td><td>${e(a.veterinarian_name)}</td><td>${e(a.service_name)}</td><td>${badge(a.status)}</td><td><div class="actions">${iconButton("Ver consulta de " + a.pet_name, "appointment-detail", a.id, null, "eye")}${["Agendado", "Confirmado"].includes(a.status) ? iconButton("Editar consulta de " + a.pet_name, "edit-appointment", a.id, null, "edit") : ""}</div></td></tr>`,
    )
    .join("");
}
export function overview(data) {
  const d = data.dashboard,
    today = data.appointments.filter((a) => a.starts_at.startsWith(d.today));
  const upcoming = data.appointments
    .filter(
      (a) =>
        a.starts_at.slice(0, 10) >= d.today &&
        ["Agendado", "Confirmado"].includes(a.status),
    )
    .slice(0, 3);
  const recent = data.appointments
    .filter((a) => a.status === "Concluído")
    .slice()
    .reverse()
    .slice(0, 4);
  return `<div class="metrics">${metric("Consultas hoje", d.appointments_today, "calendar")}${metric("Pacientes ativos", d.patients, "paw")}${metric("Receita do mês", money(d.revenue_month_cents), "chart", "Recebimentos registrados")}${metric("Em aberto", money(d.outstanding_cents), "file", "Consultas concluídas")}</div><div class="dashboard-grid">${panel("Agenda de hoje", table(["Horário", "Animal", "Tutor", "Veterinário", "Serviço", "Status", "Ações"], appointmentRows(today), "Nenhuma consulta para hoje."), `<span class="muted">${dateLabel(d.today)}</span>`)}${panel("Próximas consultas", `<div class="timeline">${upcoming.map((a) => `<div class="timeline-item"><div class="timeline-time">${a.starts_at.slice(11)}<span class="meta">${dateLabel(a.starts_at).slice(0, 5)}</span></div>${avatar(a.pet_name, a.pet_id)}<div><span class="name">${e(a.pet_name)}</span><p>${e(a.tutor_name)}</p><p>${e(a.service_name)}</p></div></div>`).join("") || '<div class="empty">A agenda está livre.</div>'}</div><div class="timeline-foot"><a class="btn" href="#agenda">Ver agenda completa</a></div>`)}</div>${panel("Últimos atendimentos", table(["Animal", "Tutor", "Data", "Serviço", "Veterinário", "Status", "Ações"], recent.map((a) => `<tr><td>${animal(a)}</td><td>${e(a.tutor_name)}</td><td>${dateLabel(a.starts_at)}</td><td>${e(a.service_name)}</td><td>${e(a.veterinarian_name)}</td><td>${badge(a.status)}</td><td>${iconButton("Ver histórico de " + a.pet_name, "history", a.pet_id, null, "eye")}</td></tr>`).join(""), "Nenhum atendimento concluído."), '<a class="btn small" href="#pets">Ver pacientes</a>')}`;
}
export function agenda(data, state) {
  let items = data.appointments.filter(
    (a) =>
      (!state.agendaDate || a.starts_at.startsWith(state.agendaDate)) &&
      (!state.status || a.status === state.status) &&
      match(a, state.query),
  );
  return `<section class="panel"><div class="toolbar"><input type="search" id="search" placeholder="Buscar animal, tutor ou veterinário" aria-label="Buscar na agenda" value="${e(state.query)}"><label for="agenda-date">Data</label><input type="date" id="agenda-date" value="${e(state.agendaDate)}"><select id="status-filter" aria-label="Filtrar por status"><option value="">Todos os status</option>${["Agendado", "Confirmado", "Concluído", "Cancelado"].map((s) => `<option ${state.status === s ? "selected" : ""}>${s}</option>`).join("")}</select>${button("Todas as datas", "all-dates", { style: "small" })}</div><div class="summary-strip"><span>${items.length} ${items.length === 1 ? "consulta" : "consultas"}</span><span>Total previsto<strong>${money(items.filter((a) => a.status !== "Cancelado").reduce((sum, a) => sum + a.fee_cents, 0))}</strong></span></div>${table(["Data / hora", "Animal", "Tutor", "Veterinário", "Serviço", "Status", "Ações"], appointmentRows(items, true), "Nenhuma consulta com esses filtros.")}</section>`;
}
export function master(data, state, page) {
  const items = data[page].filter(
    (r) => (state.archived || r.active) && match(r, state.query),
  );
  const actions = (r) =>
    `<div class="actions">${page === "pets" ? iconButton("Histórico de " + r.name, "history", r.id, null, "eye") : ""}${iconButton("Editar " + r.name, "edit-master", r.id, page, "edit")}${iconButton((r.active ? "Arquivar " : "Reativar ") + r.name, "archive-master", r.id, page, r.active ? "archive" : "check")}</div>`;
  let headers, body;
  if (page === "pets") {
    headers = ["Animal", "Tutor", "Sexo", "Peso", "Situação", "Ações"];
    body = items
      .map(
        (r) =>
          `<tr><td>${animal(r)}</td><td>${e(r.tutor_name)}</td><td>${e(r.sex)}</td><td>${r.weight_kg === null ? "Não informado" : e(r.weight_kg) + " kg"}</td><td>${badge(r.active ? "Ativo" : "Arquivado")}</td><td>${actions(r)}</td></tr>`,
      )
      .join("");
  }
  if (page === "tutors") {
    headers = [
      "Nome",
      "Contato",
      "Endereço",
      "Animais ativos",
      "Situação",
      "Ações",
    ];
    body = items
      .map(
        (r) =>
          `<tr><td><span class="name">${e(r.name)}</span></td><td>${e(r.phone)}<span class="meta">${e(r.email || "")}</span></td><td>${e(r.address || "Não informado")}</td><td>${data.pets.filter((p) => p.tutor_id === r.id && p.active).length}</td><td>${badge(r.active ? "Ativo" : "Arquivado")}</td><td>${actions(r)}</td></tr>`,
      )
      .join("");
  }
  if (page === "veterinarians") {
    headers = [
      "Nome",
      "CRMV",
      "Especialidade",
      "Telefone",
      "Situação",
      "Ações",
    ];
    body = items
      .map(
        (r) =>
          `<tr><td><span class="name">${e(r.name)}</span></td><td>${e(r.crmv)}</td><td>${e(r.specialty)}</td><td>${e(r.phone || "Não informado")}</td><td>${badge(r.active ? "Ativo" : "Arquivado")}</td><td>${actions(r)}</td></tr>`,
      )
      .join("");
  }
  if (page === "services") {
    headers = ["Serviço", "Preço", "Duração", "Situação", "Ações"];
    body = items
      .map(
        (r) =>
          `<tr><td><span class="name">${e(r.name)}</span></td><td class="number">${money(r.price_cents)}</td><td>${r.duration_minutes} min</td><td>${badge(r.active ? "Ativo" : "Arquivado")}</td><td>${actions(r)}</td></tr>`,
      )
      .join("");
  }
  return `<section class="panel"><div class="toolbar"><input type="search" id="search" aria-label="Buscar ${pages[page][0].toLowerCase()}" placeholder="Buscar ${pages[page][0].toLowerCase()}" value="${e(state.query)}"><label class="check-label"><input type="checkbox" id="archived-filter" ${state.archived ? "checked" : ""}>Mostrar arquivados</label></div>${table(headers, body, "Nenhum cadastro com esses filtros.")}</section>`;
}
export function finance(data, state) {
  const completed = data.appointments.filter((a) => a.status === "Concluído"),
    outstanding = completed.filter((a) => a.balance_cents > 0);
  const income = data.payments.reduce((s, p) => s + p.amount_cents, 0);
  let body;
  if (state.financeTab === "payments")
    body = table(
      ["Data", "Animal", "Tutor", "Forma", "Valor"],
      data.payments
        .filter((p) => match(p, state.query))
        .map(
          (p) =>
            `<tr><td>${dateLabel(p.paid_at)}</td><td><span class="name">${e(p.pet_name)}</span></td><td>${e(p.tutor_name)}</td><td>${e(p.method)}</td><td class="number">${money(p.amount_cents)}</td></tr>`,
        )
        .join(""),
      "Nenhum recebimento registrado.",
    );
  else
    body = table(
      ["Consulta", "Animal", "Tutor", "Valor", "Recebido", "Saldo", "Ações"],
      data.appointments
        .filter(
          (a) =>
            a.status !== "Cancelado" &&
            a.balance_cents > 0 &&
            match(a, state.query),
        )
        .map(
          (a) =>
            `<tr><td>${dateLabel(a.starts_at)}<span class="meta">${e(a.service_name)} · ${e(a.status)}</span></td><td>${animal(a)}</td><td>${e(a.tutor_name)}</td><td>${money(a.fee_cents)}</td><td>${money(a.received_cents)}</td><td><strong class="number">${money(a.balance_cents)}</strong></td><td>${button("Receber", "payment", { id: a.id, style: "small", icon: "wallet" })}</td></tr>`,
        )
        .join(""),
      "Nenhuma consulta com saldo pendente.",
    );
  return `<div class="metrics financial-metrics">${metric("Recebido no mês", money(data.dashboard.revenue_month_cents), "chart")}${metric("Total recebido", money(income), "wallet")}${metric("Em aberto", money(outstanding.reduce((s, a) => s + a.balance_cents, 0)), "file", "Somente consultas concluídas")}</div><section class="panel"><div class="tabs" role="group" aria-label="Visão financeira"><button class="${state.financeTab === "balances" ? "active" : ""}" data-action="finance-tab" data-tab="balances">Saldos das consultas</button><button class="${state.financeTab === "payments" ? "active" : ""}" data-action="finance-tab" data-tab="payments">Recebimentos</button></div><div class="toolbar"><input type="search" id="search" value="${e(state.query)}" aria-label="Buscar no financeiro" placeholder="Buscar animal ou tutor"><span class="muted">${state.financeTab === "balances" ? "Consultas agendadas também podem receber adiantamentos." : "Valores efetivamente recebidos."}</span></div>${body}</section>`;
}
export function documentation() {
  return `<div class="docs-grid"><section class="panel prose"><h2>Sobre o projeto</h2><p>O VetCare reúne os cadastros e os atendimentos de uma clínica veterinária. Cada consulta liga um animal, um veterinário e um serviço. O atendimento gera um prontuário, e os recebimentos ficam vinculados à consulta.</p><p>O banco SQLite contém sete tabelas. Chaves estrangeiras mantêm os vínculos, triggers bloqueiam conflitos de horário e pagamentos acima do saldo, e uma view calcula os valores pendentes.</p><h3>Para apresentar o sistema</h3><ol><li>Cadastre um tutor e seu animal.</li><li>Agende uma consulta e tente repetir o horário.</li><li>Conclua o atendimento preenchendo o prontuário.</li><li>Registre um pagamento parcial e confira o saldo.</li><li>Abra o histórico do paciente.</li></ol><p>Os dados iniciais são fictícios. Esta versão foi feita para uso local e apresentação acadêmica. Ela não inclui contas de usuário, estoque ou estornos.</p></section><section class="panel"><div class="panel-head"><h2>Material técnico</h2></div><div class="doc-links"><a class="btn" href="/docs/relatorio-tecnico.pdf" target="_blank" rel="noopener">${icon("book")}Relatório técnico em PDF</a><a class="btn" href="/docs/modelagem.svg" target="_blank" rel="noopener">${icon("file")}Diagrama do banco</a><a class="btn" href="/docs/documentacao.md" target="_blank" rel="noopener">${icon("file")}Documentação em Markdown</a></div><div class="panel-body"><h3>Stack</h3><p class="muted">Python, Flask e SQLite<br>HTML, CSS e JavaScript<br>Sem compilação do frontend</p></div></section></div>`;
}
