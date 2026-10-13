/** Formulários reutilizáveis de cadastro, agendamento, prontuário e recebimento. */
import { escapeHTML as e, money, showModal, button, dateLabel } from "./ui.js";
const options = (items, selected) =>
  items
    .map(
      ([value, label]) =>
        `<option value="${e(value)}" ${String(value) === String(selected) ? "selected" : ""}>${e(label)}</option>`,
    )
    .join("");
function field(name, label, value = "", settings = {}) {
  const base = `id="field-${name}" name="${name}" ${settings.required ? "required" : ""} ${settings.autofocus ? "autofocus" : ""}`;
  let input;
  if (settings.options)
    input = `<select ${base}>${options(settings.options, value)}</select>`;
  else if (settings.textarea)
    input = `<textarea ${base} maxlength="4000">${e(value)}</textarea>`;
  else
    input = `<input ${base} type="${settings.type || "text"}" value="${e(value)}" ${settings.maxlength ? `maxlength="${settings.maxlength}"` : ""} ${settings.min !== undefined ? `min="${settings.min}"` : ""} ${settings.max !== undefined ? `max="${settings.max}"` : ""} ${settings.step ? `step="${settings.step}"` : ""}>`;
  return `<div class="field ${settings.wide ? "wide" : ""}"><label for="field-${name}">${e(label)}${settings.required ? " *" : ""}</label>${input}${settings.hint ? `<span class="hint">${e(settings.hint)}</span>` : ""}</div>`;
}
function form(
  title,
  fields,
  endpoint,
  method = "POST",
  info = "",
  submit = "Salvar",
) {
  showModal(
    title,
    `<form id="data-form" data-endpoint="${endpoint}" data-method="${method}"><div class="modal-body"><p class="form-error" role="alert"></p>${info ? `<p class="form-info">${e(info)}</p>` : ""}<div class="form-grid">${fields}</div><p class="meta">* Campo obrigatório</p></div><div class="modal-actions">${button("Cancelar", "close-modal")}<button type="submit" class="btn primary">${e(submit)}</button></div></form>`,
  );
}
export function masterForm(table, data, record = null) {
  const r = record || {};
  let fields;
  if (table === "tutors")
    fields =
      field("name", "Nome", r.name, {
        required: true,
        autofocus: true,
        maxlength: 100,
        wide: true,
      }) +
      field("phone", "Telefone", r.phone, {
        required: true,
        type: "tel",
        maxlength: 25,
      }) +
      field("email", "E-mail", r.email, { type: "email", maxlength: 150 }) +
      field("address", "Endereço", r.address, { wide: true, maxlength: 250 });
  if (table === "pets")
    fields =
      field("name", "Nome do animal", r.name, {
        required: true,
        autofocus: true,
        maxlength: 80,
      }) +
      `<fieldset class="field wide tutor-picker"><legend>Tutores *</legend><p class="hint">Selecione todos os responsáveis pelo pet. Na consulta, você escolherá quem o acompanha.</p><div class="tutor-options">${data.tutors.filter(t => t.active).map(t => `<label class="check-label"><input type="checkbox" name="tutor_ids" value="${t.id}" ${(r.tutor_ids || []).includes(t.id) ? "checked" : ""}>${e(t.name)}</label>`).join("") || '<p>Cadastre um tutor ativo antes de cadastrar o pet.</p>'}</div></fieldset>` +
      field("species", "Espécie", r.species || "Cão", {
        required: true,
        options: ["Cão", "Gato", "Ave", "Outro"].map((x) => [x, x]),
      }) +
      field("breed", "Raça", r.breed, { maxlength: 80 }) +
      field("sex", "Sexo", r.sex || "Não informado", {
        required: true,
        options: ["Não informado", "Macho", "Fêmea"].map((x) => [x, x]),
      }) +
      field("birth_date", "Nascimento", r.birth_date, {
        type: "date",
        max: data.dashboard.today,
      }) +
      field("weight_kg", "Peso (kg)", r.weight_kg, {
        type: "number",
        min: "0.001",
        max: 1000,
        step: "any",
      }) +
      field("notes", "Observações", r.notes, { textarea: true, wide: true });
  if (table === "veterinarians")
    fields =
      field("name", "Nome", r.name, {
        required: true,
        autofocus: true,
        maxlength: 100,
        wide: true,
      }) +
      field("crmv", "CRMV com UF", r.crmv, { required: true, maxlength: 30 }) +
      field("phone", "Telefone", r.phone, { type: "tel", maxlength: 25 }) +
      field("specialty", "Especialidade", r.specialty || "Clínica geral", {
        required: true,
        wide: true,
        maxlength: 100,
      });
  if (table === "services")
    fields =
      field("name", "Nome do serviço", r.name, {
        required: true,
        autofocus: true,
        maxlength: 100,
        wide: true,
      }) +
      field(
        "price",
        "Preço (R$)",
        r.price_cents !== undefined ? (r.price_cents / 100).toFixed(2) : "",
        { required: true, type: "number", min: 0, max: 1000000, step: "0.01" },
      ) +
      field("duration_minutes", "Duração (min)", r.duration_minutes || 30, {
        required: true,
        type: "number",
        min: 10,
        max: 240,
        step: 1,
      });
  const nouns = {
    tutors: "tutor",
    pets: "paciente",
    veterinarians: "veterinário",
    services: "serviço",
  };
  form(
    `${record ? "Editar" : "Novo"} ${nouns[table]}`,
    fields,
    `/${table}${record ? "/" + record.id : ""}`,
    record ? "PATCH" : "POST",
  );
}
function companionOptions(data, petId) {
  const pet = data.pets.find(p => p.id === Number(petId));
  return [["", "Selecione quem acompanha o pet"], ...data.tutors.filter(t => t.active && pet?.tutor_ids.includes(t.id)).map(t => [t.id, t.name])];
}
function companionField(data, petId, selected) {
  return field("accompanying_tutor_id", "Tutor acompanhante", selected || "", {
    required: true, wide: true, options: companionOptions(data, petId),
    hint: "Pessoa que acompanha o paciente nesta consulta.",
  });
}
export function updateCompanionOptions(data, petId) {
  const select = document.querySelector("#field-accompanying_tutor_id");
  if (select) select.innerHTML = options(companionOptions(data, petId), "");
}
export function appointmentForm(data, record = null, day = null) {
  const r = record || {};
  const fields =
    field("pet_id", "Paciente", r.pet_id, {
      required: true,
      autofocus: true,
      wide: true,
      options: [
        ["", "Selecione um paciente"],
        ...data.pets
          .filter((p) => p.active || p.id === r.pet_id)
          .map((p) => [p.id, `${p.name} · ${p.tutor_name}`]),
      ],
    }) +
    companionField(data, r.pet_id, r.accompanying_tutor_id) +
    field("veterinarian_id", "Veterinário", r.veterinarian_id, {
      required: true,
      options: [
        ["", "Selecione"],
        ...data.veterinarians
          .filter((v) => v.active || v.id === r.veterinarian_id)
          .map((v) => [v.id, v.name]),
      ],
    }) +
    field("service_id", "Serviço", r.service_id, {
      required: true,
      options: [
        ["", "Selecione"],
        ...data.services
          .filter((s) => s.active || s.id === r.service_id)
          .map((s) => [
            s.id,
            `${s.name} · ${money(s.price_cents)} · ${s.duration_minutes} min`,
          ]),
      ],
    }) +
    field(
      "starts_at",
      "Data e horário",
      r.starts_at || `${day || data.dashboard.today}T09:00`,
      { type: "datetime-local", required: true, wide: true },
    ) +
    field("notes", "Observações", r.notes, { textarea: true, wide: true });
  form(
    record ? "Editar agendamento" : "Novo agendamento",
    fields,
    `/appointments${record ? "/" + record.id : ""}`,
    record ? "PATCH" : "POST",
    "O sistema verifica conflitos de horário. Preço e duração são definidos pelo serviço.",
  );
}
export function recordForm(data, appointment) {
  const pet = data.pets.find((p) => p.id === appointment.pet_id);
  form(
    `Atendimento de ${appointment.pet_name}`,
    companionField(data, appointment.pet_id, appointment.accompanying_tutor_id) +
    field("complaint", "Queixa / motivo da consulta", "", {
      required: true,
      autofocus: true,
      textarea: true,
      wide: true,
    }) +
      field("diagnosis", "Avaliação / diagnóstico", "", {
        required: true,
        textarea: true,
        wide: true,
      }) +
      field("treatment", "Conduta / orientações", "", {
        textarea: true,
        wide: true,
      }) +
      field("weight_kg", "Peso aferido (kg)", pet?.weight_kg, {
        type: "number",
        min: "0.001",
        max: 1000,
        step: "any",
      }),
    `/appointments/${appointment.id}/record`,
    "POST",
    `${appointment.service_name} · ${dateLabel(appointment.starts_at)}. Ao salvar, a consulta será concluída. O prontuário não poderá ser editado.`,
    "Concluir atendimento",
  );
}
export function paymentForm(data, appointment) {
  form(
    `Receber de ${appointment.pet_name}`,
    field("appointment_id", "Consulta", appointment.id, {
      required: true,
      wide: true,
      options: [
        [
          appointment.id,
          `${appointment.service_name} · ${dateLabel(appointment.starts_at)}`,
        ],
      ],
    }) +
      field(
        "amount",
        "Valor recebido (R$)",
        (appointment.balance_cents / 100).toFixed(2),
        {
          required: true,
          autofocus: true,
          type: "number",
          min: "0.01",
          max: appointment.balance_cents / 100,
          step: "0.01",
        },
      ) +
      field("method", "Forma de pagamento", "Pix", {
        required: true,
        options: ["Pix", "Dinheiro", "Cartão"].map((x) => [x, x]),
      }) +
      field("paid_at", "Data do pagamento", data.dashboard.today, {
        required: true,
        type: "date",
        max: data.dashboard.today,
        wide: true,
      }),
    "/payments",
    "POST",
    `Saldo: ${money(appointment.balance_cents)}. Pagamentos parciais são permitidos. Recebimentos não podem ser editados ou estornados neste projeto.`,
    "Registrar recebimento",
  );
}
