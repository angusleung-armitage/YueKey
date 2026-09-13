-- Only Quick-specific key behavior lives here. Rime owns selection and learning.
local M = {processor = {}, visibility = {}}
local REJECTED, ACCEPTED, NOOP = 0, 1, 2

local function reveal(ctx)
  ctx:set_option('_quick_hk_revealed', true)
  ctx:refresh_non_confirmed_composition()
end

local function confirm_without_prediction(ctx)
  local prediction = ctx:get_option('prediction')
  ctx:set_option('prediction', false)
  ctx:confirm_current_selection()
  ctx:clear()
  return prediction
end

function M.processor.init(env)
  env.show = env.engine.schema.config:get_bool('quick_hk/show_candidates') ~= false
end

function M.processor.func(key, env)
  local ctx = env.engine.context
  if key:release() then return NOOP end
  -- Stop the processor chain: downstream Rime editors otherwise consume some
  -- application shortcuts (for example Ctrl+Backspace on a prediction menu).
  if key:ctrl() or key:alt() or key:super() then return REJECTED end
  if ctx:get_option('ascii_mode') then return NOOP end
  local input = ctx.input
  local code = key.keycode

  if code == 0xff1b then -- Escape cancels suggestions and input without committing.
    return NOOP -- The predictor and editor handle this together.
  end
  if code == 0x20 and input ~= '' and not env.show and
      not ctx:get_option('_quick_hk_revealed') then
    reveal(ctx)
    return ACCEPTED
  end
  if code >= 0x61 and code <= 0x7a and not key:shift() then
    if #input >= 2 then
      if not env.show then reveal(ctx) end
      local candidate = ctx:get_selected_candidate()
      if not candidate or candidate.text:match('^[a-z]+$') then return ACCEPTED end -- Keep invalid code editable.
      local prediction = confirm_without_prediction(ctx)
      ctx:set_option('_quick_hk_revealed', false)
      ctx:push_input(string.char(code))
      ctx:set_option('prediction', prediction)
      return ACCEPTED
    end
    -- Typing a new code dismisses a prediction; it must never accept it.
    local candidate = ctx:get_selected_candidate()
    if input == '' and candidate and candidate.type == 'prediction' then
      local prediction = ctx:get_option('prediction')
      ctx:set_option('prediction', false)
      ctx:clear()
      ctx:set_option('_quick_hk_revealed', false)
      ctx:push_input(string.char(code))
      ctx:set_option('prediction', prediction)
      return ACCEPTED
    end
    ctx:set_option('_quick_hk_revealed', false)
    return NOOP
  end
  -- Never turn an unmatched Quick code into Latin text by pressing Space.
  if code == 0x20 and input ~= '' then
    local candidate = ctx:get_selected_candidate()
    if not candidate or candidate.text:match('^[a-z]+$') then return ACCEPTED end
  end
  return NOOP
end

function M.visibility.func(translation, env)
  local ctx = env.engine.context
  local show = env.engine.schema.config:get_bool('quick_hk/show_candidates') ~= false
  if not show and ctx.input ~= '' and not ctx:get_option('_quick_hk_revealed') then
    return
  end
  for candidate in translation:iter() do yield(candidate) end
end

return M
