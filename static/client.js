/** Cliente de mesma origem. Erros da API são exibidos junto ao formulário. */
export async function request(path, method = "GET", body = null) {
  const response = await fetch("/api" + path, {
    method,
    headers: {
      "Content-Type": "application/json",
      "X-CSRF-Token": document.querySelector("meta[name=csrf-token]").content,
    },
    ...(body ? { body: JSON.stringify(body) } : {}),
  });
  let data;
  try {
    data = await response.json();
  } catch {
    throw new Error(
      "Resposta inesperada. Confira se o servidor está em execução.",
    );
  }
  if (!response.ok)
    throw new Error(data.error || "Não foi possível concluir a operação.");
  return data;
}
