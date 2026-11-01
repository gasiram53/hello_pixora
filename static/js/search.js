(() => {
  const page = document.querySelector("[data-search-page]");
  if (!page) return;

  const form = page.querySelector("[data-search-form]");
  const input = page.querySelector("[data-search-input]");
  const typeInput = page.querySelector("[data-search-type]");
  const clearButton = page.querySelector("[data-search-clear]");
  const suggestions = page.querySelector("[data-search-suggestions]");
  const suggestionResults = page.querySelector("[data-suggestion-results]");
  const suggestionMessage = page.querySelector("[data-suggestion-message]");
  const suggestionLabel = page.querySelector("[data-suggestion-label]");
  const suggestionsUrl = page.dataset.suggestionsUrl;
  const termsKey = "pixora:recent-searches";
  const peopleKey = "pixora:recent-search-people";
  let debounceTimer;
  let activeRequest;

  const readStorage = (key) => {
    try {
      const value = JSON.parse(localStorage.getItem(key) || "[]");
      return Array.isArray(value) ? value : [];
    } catch (error) {
      console.error("Could not read search history.", error);
      return [];
    }
  };

  const writeStorage = (key, value) => {
    try {
      localStorage.setItem(key, JSON.stringify(value));
    } catch (error) {
      console.error("Could not save search history.", error);
    }
  };

  const saveTerm = (term) => {
    const normalized = term.trim().slice(0, 80);
    if (!normalized) return;
    const terms = readStorage(termsKey).filter((item) => typeof item === "string" && item.toLowerCase() !== normalized.toLowerCase());
    writeStorage(termsKey, [normalized, ...terms].slice(0, 8));
  };

  const savePerson = (person) => {
    if (!person.username || !person.profile_url) return;
    const people = readStorage(peopleKey).filter((item) => item.username !== person.username);
    writeStorage(peopleKey, [person, ...people].slice(0, 8));
  };

  const createAvatar = (person, className = "person-avatar") => {
    const avatar = document.createElement("span");
    avatar.className = className;
    if (person.avatar_url) {
      const image = document.createElement("img");
      image.src = person.avatar_url;
      image.alt = "";
      avatar.append(image);
    } else {
      avatar.textContent = (person.username || "?").slice(0, 1).toLocaleUpperCase();
    }
    return avatar;
  };

  const createPersonLink = (person, className = "suggestion-row") => {
    const link = document.createElement("a");
    link.className = className;
    link.href = person.profile_url;
    link.dataset.personResult = "";
    link.dataset.username = person.username;
    link.dataset.fullName = person.full_name;
    link.dataset.profileUrl = person.profile_url;
    link.dataset.avatarUrl = person.avatar_url || "";
    link.append(createAvatar(person, className === "suggestion-row" ? "person-avatar" : "person-avatar"));

    const copy = document.createElement("span");
    copy.className = className === "suggestion-row" ? "suggestion-copy" : "person-details";
    const fullName = document.createElement("strong");
    fullName.textContent = person.full_name;
    const username = document.createElement("span");
    username.textContent = `@${person.username}`;
    copy.append(fullName, username);
    if (person.bio) {
      const bio = document.createElement("small");
      bio.textContent = person.bio;
      copy.append(bio);
    }
    link.append(copy);
    return link;
  };

  const renderHistory = () => {
    const history = page.querySelector("[data-search-history]");
    const termList = page.querySelector("[data-recent-searches]");
    const peopleList = page.querySelector("[data-recent-people]");
    const peopleWrap = page.querySelector("[data-recent-people-wrap]");
    if (!history || !termList || !peopleList || !peopleWrap) return;
    const terms = readStorage(termsKey).filter((item) => typeof item === "string");
    const people = readStorage(peopleKey).filter((item) => item && typeof item.username === "string");
    termList.replaceChildren();
    peopleList.replaceChildren();

    terms.forEach((term) => {
      const chip = document.createElement("span");
      chip.className = "recent-search-chip";
      const link = document.createElement("a");
      const target = new URL(form.action, window.location.href);
      target.searchParams.set("q", term);
      target.searchParams.set("type", typeInput.value);
      link.href = target.toString();
      link.textContent = term;
      const remove = document.createElement("button");
      remove.type = "button";
      remove.textContent = "×";
      remove.setAttribute("aria-label", `Remove recent search ${term}`);
      remove.addEventListener("click", () => {
        writeStorage(termsKey, readStorage(termsKey).filter((item) => item !== term));
        renderHistory();
      });
      chip.append(link, remove);
      termList.append(chip);
    });

    people.forEach((person) => peopleList.append(createPersonLink(person, "person-main")));
    peopleWrap.hidden = people.length === 0;
    history.hidden = terms.length === 0 && people.length === 0;
  };

  const showSuggestions = (open) => {
    if (!suggestions) return;
    suggestions.hidden = !open;
    input.setAttribute("aria-expanded", String(open));
  };

  const renderSuggestions = (people) => {
    suggestionResults.replaceChildren();
    people.forEach((person) => suggestionResults.append(createPersonLink(person)));
    suggestionLabel.hidden = people.length === 0;
  };

  const searchSuggestions = async () => {
    const term = input.value.trim();
    if (activeRequest) activeRequest.abort();
    if (term.length < 2) {
      renderSuggestions([]);
      suggestionMessage.hidden = true;
      showSuggestions(false);
      return;
    }
    activeRequest = new AbortController();
    suggestionMessage.hidden = false;
    suggestionMessage.textContent = "Searching people…";
    showSuggestions(true);

    try {
      const response = await fetch(`${suggestionsUrl}?q=${encodeURIComponent(term)}`, {
        headers: { Accept: "application/json" },
        signal: activeRequest.signal,
      });
      if (!response.ok) throw new Error(`Search suggestions failed (${response.status}).`);
      const people = await response.json();
      renderSuggestions(people);
      suggestionMessage.textContent = people.length ? "" : "No people found. Try another name or username.";
      suggestionMessage.hidden = people.length > 0;
    } catch (error) {
      if (error.name === "AbortError") return;
      renderSuggestions([]);
      suggestionMessage.textContent = "Suggestions are unavailable. You can still submit your search.";
      suggestionMessage.hidden = false;
      console.error(error);
    }
  };

  if (input) {
    input.addEventListener("input", () => {
      clearButton.hidden = input.value.length === 0;
      window.clearTimeout(debounceTimer);
      debounceTimer = window.setTimeout(searchSuggestions, 250);
    });
    input.addEventListener("focus", () => {
      if (input.value.trim().length >= 2 && suggestions.hidden) searchSuggestions();
    });
    input.addEventListener("keydown", (event) => {
      if (event.key === "Escape") showSuggestions(false);
    });
  }

  if (clearButton) {
    clearButton.addEventListener("click", () => {
      input.value = "";
      clearButton.hidden = true;
      renderSuggestions([]);
      showSuggestions(false);
      input.focus();
    });
  }

  if (form) {
    form.addEventListener("submit", () => {
      saveTerm(input.value);
      showSuggestions(false);
    });
  }

  page.addEventListener("click", (event) => {
    const result = event.target.closest("[data-person-result]");
    if (result) {
      savePerson({
        username: result.dataset.username,
        full_name: result.dataset.fullName,
        profile_url: result.dataset.profileUrl,
        avatar_url: result.dataset.avatarUrl || null,
      });
      return;
    }
    if (!form.contains(event.target)) showSuggestions(false);
  });

  const clearTerms = page.querySelector("[data-clear-search-history]");
  if (clearTerms) {
    clearTerms.addEventListener("click", () => {
      writeStorage(termsKey, []);
      writeStorage(peopleKey, []);
      renderHistory();
    });
  }

  const clearPeople = page.querySelector("[data-clear-recent-people]");
  if (clearPeople) {
    clearPeople.addEventListener("click", () => {
      writeStorage(peopleKey, []);
      renderHistory();
    });
  }

  page.querySelectorAll(".search-tab").forEach((tab) => {
    tab.addEventListener("click", () => {
      typeInput.value = new URL(tab.href).searchParams.get("type") || "all";
    });
  });

  renderHistory();
})();
