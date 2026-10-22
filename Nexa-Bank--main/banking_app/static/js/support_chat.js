const SUPPORT_STOP_WORDS = new Set([
  'a', 'about', 'an', 'and', 'are', 'can', 'do', 'for', 'how', 'i', 'in', 'is', 'it',
  'me', 'my', 'of', 'on', 'or', 'please', 'the', 'to', 'what', 'where', 'which', 'with',
  'would', 'you', 'your',
]);

function tokenizeSupportText(value) {
  return value.toLowerCase().match(/[a-z0-9]+/g) || [];
}

function parseSupportKnowledge(markdown) {
  const sections = markdown.split(/^##\s+/m).slice(1);
  const articles = [];

  sections.forEach(section => {
    const [titleLine, ...lines] = section.trim().split(/\r?\n/);
    const fields = {};
    lines.forEach(line => {
      const match = line.match(/^(Answer|Keywords|Details|Link|Link label):\s*(.+)$/);
      if (match) fields[match[1].toLowerCase().replace(' ', '_')] = match[2].trim();
    });

    const href = fields.link || '';
    if (
      !titleLine
      || !fields.answer
      || !fields.keywords
      || !fields.details
      || !fields.link_label
      || !/^\/(?!\/)[a-z0-9_/#?=&.-]*$/i.test(href)
    ) return;

    articles.push({
      title: titleLine.trim(),
      answer: fields.answer,
      keywords: fields.keywords,
      details: fields.details,
      href,
      link: fields.link_label,
    });
  });

  return articles;
}

function buildSupportIndex(articles) {
  const documents = articles.map(article => {
    const frequencies = new Map();
    const terms = tokenizeSupportText(`${article.title} ${article.keywords} ${article.details}`);
    terms.forEach(term => frequencies.set(term, (frequencies.get(term) || 0) + 1));
    return { article, frequencies, length: terms.length };
  });
  const documentFrequencies = new Map();

  documents.forEach(document => {
    document.frequencies.forEach((_, term) => {
      documentFrequencies.set(term, (documentFrequencies.get(term) || 0) + 1);
    });
  });

  return { documents, documentFrequencies };
}

function rankSupportArticles(question, index) {
  const queryTerms = [...new Set(
    tokenizeSupportText(question).filter(term => !SUPPORT_STOP_WORDS.has(term))
  )];
  if (!queryTerms.length || !index.documents.length) return [];

  const averageLength = index.documents.reduce((sum, document) => sum + document.length, 0)
    / index.documents.length || 1;
  const totalDocuments = index.documents.length;

  const scored = index.documents.map(document => {
    const score = queryTerms.reduce((total, term) => {
      const frequency = document.frequencies.get(term) || 0;
      if (!frequency) return total;
      const documentFrequency = index.documentFrequencies.get(term) || 0;
      const inverseDocumentFrequency = Math.log(
        1 + (totalDocuments - documentFrequency + 0.5) / (documentFrequency + 0.5)
      );
      const lengthNormalization = frequency
        + 1.2 * (0.25 + 0.75 * document.length / averageLength);
      return total + inverseDocumentFrequency * (frequency * 2.2 / lengthNormalization);
    }, 0);
    const phraseBoost = document.article.title.toLowerCase().includes(question.trim().toLowerCase())
      ? 2
      : 0;
    return { article: document.article, score: score + phraseBoost };
  }).sort((first, second) => second.score - first.score);

  if (!scored.length || scored[0].score < 0.35) return [];
  return scored.slice(0, 2).filter((item, indexInResults, matches) => (
    item.score >= matches[0].score * 0.68
  ));
}

let supportIndex = { documents: [], documentFrequencies: new Map() };
let supportKnowledgeError = null;

async function loadSupportKnowledge(url) {
  if (!url) throw new Error('The help knowledge document URL is missing.');
  const response = await fetch(url, { credentials: 'same-origin' });
  if (!response.ok) throw new Error(`Help knowledge request failed (${response.status}).`);

  const markdown = await response.text();
  const articles = parseSupportKnowledge(markdown);
  if (!articles.length) throw new Error('The help knowledge document contains no valid articles.');

  supportIndex = buildSupportIndex(articles);
  return articles.length;
}

window.NexaBankSupportSearch = {
  ready: Promise.resolve(0),
  load(url) {
    this.ready = loadSupportKnowledge(url);
    return this.ready;
  },
  search(question) {
    return rankSupportArticles(question, supportIndex).map(({ article, score }) => ({
      title: article.title,
      answer: article.answer,
      href: article.href,
      link: article.link,
      score,
    }));
  },
};

function initSupportChat() {
  const launcher = document.getElementById('supportChatLauncher');
  const panel = document.getElementById('supportChatPanel');
  const closeButton = document.getElementById('supportChatClose');
  const form = document.getElementById('supportChatForm');
  const input = document.getElementById('supportChatInput');
  const messages = document.getElementById('supportChatMessages');
  if (!launcher || !panel || !closeButton || !form || !input || !messages) return;

  const status = document.getElementById('supportChatStatus');
  const knowledgeUrl = launcher.closest('.support-chat').dataset.knowledgeUrl;

  function appendMessage(text, sender) {
    const message = document.createElement('div');
    message.className = `support-chat-message ${sender}`;
    message.textContent = text;
    messages.appendChild(message);
  }

  function appendSource(article) {
    const link = document.createElement('a');
    link.className = 'support-chat-link';
    link.href = article.href;
    link.textContent = `Source: ${article.title} · ${article.link}`;
    messages.appendChild(link);
  }

  function submitQuestion(question) {
    const normalized = question.trim().slice(0, 240);
    if (!normalized) return;

    appendMessage(normalized, 'user');
    if (supportKnowledgeError) {
      appendMessage('I could not load the local help document. Please try again later.', 'bot');
      return;
    }

    const results = window.NexaBankSupportSearch.search(normalized);
    if (!results.length) {
      appendMessage('I couldn’t find a relevant answer in the local help guide. Try asking about transfers, withdrawals, statements, settings, or KYC.', 'bot');
    } else {
      results.forEach(result => {
        appendMessage(result.answer, 'bot');
        appendSource(result);
      });
    }
    messages.scrollTop = messages.scrollHeight;
  }

  function setOpen(open) {
    panel.classList.toggle('is-open', open);
    panel.setAttribute('aria-hidden', String(!open));
    launcher.setAttribute('aria-expanded', String(open));
    launcher.setAttribute('aria-label', open ? 'Close help chat' : 'Open help chat');
    if (open) input.focus();
  }

  window.NexaBankSupportSearch.load(knowledgeUrl)
    .then(articleCount => {
      if (status) status.textContent = `Local help search · ${articleCount} topics`;
    })
    .catch(error => {
      supportKnowledgeError = error;
      console.error('Unable to load the NexaBank help document:', error);
      if (status) status.textContent = 'Help guide unavailable';
    });

  launcher.addEventListener('click', () => setOpen(!panel.classList.contains('is-open')));
  closeButton.addEventListener('click', () => {
    setOpen(false);
    launcher.focus();
  });
  form.addEventListener('submit', async event => {
    event.preventDefault();
    await window.NexaBankSupportSearch.ready;
    submitQuestion(input.value);
    input.value = '';
    input.focus();
  });
  messages.querySelectorAll('[data-chat-question]').forEach(button => {
    button.addEventListener('click', async () => {
      await window.NexaBankSupportSearch.ready;
      submitQuestion(button.dataset.chatQuestion);
    });
  });
  document.addEventListener('keydown', event => {
    if (event.key === 'Escape' && panel.classList.contains('is-open')) {
      setOpen(false);
      launcher.focus();
    }
  });
}

document.addEventListener('DOMContentLoaded', initSupportChat);
