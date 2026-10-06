# Hospedagem na Vercel

O backend Flask mantém o SQLite. `cloud_db.py` adapta a persistência ao ambiente de funções sem usar o disco temporário como fonte de dados.

## Fluxo de uma requisição

1. A função usa sua identidade OIDC para ler `vetcare/production.sqlite3` no Blob privado. Em Preview, usa `vetcare/preview.sqlite3`.
2. A leitura inclui `cache=0`, garantindo a versão mais recente, e recebe o ETag da imagem.
3. `sqlite3.Connection.deserialize` abre a imagem em memória. A conexão habilita as chaves estrangeiras.
4. As rotas executam as mesmas consultas e transações da aplicação local.
5. Após uma alteração bem-sucedida, `serialize` produz uma imagem. Um PUT com `x-if-match` salva somente se o ETag original ainda for atual.
6. Um conflito retorna HTTP 409. A alteração daquela requisição é descartada com a conexão em memória. O usuário deve recarregar e repetir a operação.
7. Erros de armazenamento retornam HTTP 503. Nenhuma gravação é anunciada como confirmada antes do retorno do Blob.

A primeira leitura cria o esquema e o seed se o objeto não existir. A criação proíbe sobrescrita; se outro acesso criou o banco, a função lê o objeto vencedor. Consultas de leitura não gravam novamente a imagem.

## Configuração

- Framework Flask, Python e região `gru1`, conforme `vercel.json`.
- Blob privado `vetcare-sqlite`, em `gru1`, conectado apenas ao VetCare.
- OIDC em Production e Preview, sem token permanente no código.
- Repositório privado PedroPrebeck/vetcare, branch main.
- Arquivos de QA, banco local e ambiente virtual excluídos da implantação.

O adaptador HTTP segue o protocolo do SDK oficial `@vercel/blob` 2.8.1, versão da API 12. Usa a biblioteca padrão do Python para evitar depender de Node no runtime Python.

## Limites e segurança

A imagem inteira é baixada a cada requisição de dados e enviada a cada gravação. O limite de 4 MiB é uma escolha do projeto. As cotas de operações e transferência do plano Hobby continuam aplicáveis. A configuração é para apresentação acadêmica, sem teste de carga ou garantia de operação clínica.

Não há autenticação de usuários da clínica. O aviso da interface pede apenas dados fictícios. A proteção da implantação da Vercel pode exigir login para acessar o site, conforme a configuração da conta. O Blob privado não é servido ao navegador. Os dados são compartilhados entre visitantes autorizados a acessar a implantação.

CSRF na nuvem usa double-submit com cookie `__Host-vetcare-csrf`, Secure, HttpOnly e SameSite=Strict. O token também aparece no HTML da própria origem e é enviado no cabeçalho das escritas. O prefixo __Host impede definir o cookie para um domínio pai. O modo local mantém a sessão Flask.

Para backup online, baixe o objeto SQLite pelo painel Manage Blobs com a conta autorizada. O comando `backup-db` documentado no README atende ao banco local.

## Verificação

A suíte contém 22 testes das regras e seis testes da persistência remota simulada. Ela cobre leitura sem gravação, persistência entre instâncias, conflito sem sobrescrita, erro de armazenamento sem falso sucesso e CSRF. A implantação real é verificada após o build.

## Fontes

- https://vercel.com/docs/frameworks/backend/flask
- https://vercel.com/docs/vercel-blob/using-blob-sdk
- https://vercel.com/changelog/vercel-blob-now-supports-consistent-reads-on-private-storage
- https://github.com/vercel/storage/tree/main/packages/blob
