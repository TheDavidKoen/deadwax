const API_ROOT = 'https://generativelanguage.googleapis.com/v1beta';

const BOLD = '[1m';
const RESET = '[0m';

const DEFAULT_PROMPT =
  'In one sentence, what makes a good running order for an album?';

function readApiKey() {
  const key = process.env.GEMINI_API_KEY;
  if (key) return key;

  console.error('GEMINI_API_KEY is not set.');
  console.error('');
  console.error('  1. Get a free key at https://aistudio.google.com/apikey');
  console.error('  2. cp .env.example .env');
  console.error('  3. Paste the key after GEMINI_API_KEY=');
  process.exit(1);
}

function readModel() {
  const model = process.env.GEMINI_MODEL;
  if (model) return model;

  console.error('GEMINI_MODEL is not set. Run `npm run models` to see what your key can reach.');
  process.exit(1);
}

function heading(text) {
  console.log('');
  console.log(`${BOLD}${text}${RESET}`);
  console.log('-'.repeat(text.length));
}

function show(value) {
  console.log(typeof value === 'string' ? value : JSON.stringify(value, null, 2));
}

async function listModels(apiKey) {
  const response = await fetch(`${API_ROOT}/models`, {
    headers: { 'x-goog-api-key': apiKey }
  });

  const body = await response.json();

  if (!response.ok) {
    heading(`Request failed with ${response.status}`);
    show(body);
    process.exit(1);
  }

  heading('Models that support generateContent');
  for (const model of body.models) {
    if (!model.supportedGenerationMethods?.includes('generateContent')) continue;
    console.log(`${model.name.replace('models/', '').padEnd(42)}${model.displayName}`);
  }
  console.log('');
  console.log('Put one of these in .env as GEMINI_MODEL.');
}

async function generate({ apiKey, model, prompt }) {
  const url = `${API_ROOT}/models/${model}:generateContent`;

  const headers = {
    'content-type': 'application/json',
    'x-goog-api-key': apiKey
  };

  const requestBody = {
    contents: [
      {
        role: 'user',
        parts: [{ text: prompt }]
      }
    ],
    generationConfig: {
      temperature: 0.7,
      maxOutputTokens: 256
    }
  };

  heading('Request');
  show(`POST ${url}`);
  show({ ...headers, 'x-goog-api-key': `${apiKey.slice(0, 6)}...redacted` });
  show(requestBody);

  const startedAt = performance.now();

  const response = await fetch(url, {
    method: 'POST',
    headers,
    body: JSON.stringify(requestBody)
  });

  const elapsedMs = Math.round(performance.now() - startedAt);
  const responseBody = await response.json();

  heading(`Response - ${response.status} ${response.statusText} in ${elapsedMs}ms`);
  show(responseBody);

  if (!response.ok) {
    heading('That failed');
    show('400 is usually a malformed body or an unknown model name.');
    show('403 means the key is wrong. 429 means you have hit the free-tier rate limit.');
    process.exit(1);
  }

  const [candidate] = responseBody.candidates;

  heading('The part you actually wanted');
  show(candidate.content.parts.map((part) => part.text).join(''));

  heading('What it cost');
  show({
    finishReason: candidate.finishReason,
    modelVersion: responseBody.modelVersion,
    ...responseBody.usageMetadata
  });
}

const args = process.argv.slice(2);
const apiKey = readApiKey();

if (args.includes('--list')) {
  await listModels(apiKey);
} else {
  const prompt = args.filter((arg) => !arg.startsWith('--')).join(' ') || DEFAULT_PROMPT;
  await generate({ apiKey, model: readModel(), prompt });
}
