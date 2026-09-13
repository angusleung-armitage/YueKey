-- SPDX-License-Identifier: MIT
-- Portable continuations for Weasel. Rime still owns selection and learning.
local M = {}
local function lookup(env, query)
  local first = utf8.codepoint(query)
  if not first then return nil end
  local bucket = string.format('%x', math.floor(first / 256))
  if not env.buckets[bucket] then
    local file = io.open(env.directory .. '/' .. bucket .. '.tsv', 'rb')
    if not file then return nil end
    local entries = {}
    for line in file:lines() do
      local prefix, suffix = line:match('^([^\t]+)\t([^\t]+)\t')
      if prefix then
        entries[prefix] = entries[prefix] or {}
        table.insert(entries[prefix], suffix)
      end
    end
    file:close()
    -- Bound the per-engine cache. Only public dictionary data is cached.
    if #env.order >= 8 then env.buckets[table.remove(env.order, 1)] = nil end
    env.buckets[bucket] = entries
    table.insert(env.order, bucket)
  end
  return env.buckets[bucket][query]
end

function M.init(env)
  env.buckets, env.order = {}, {}
  env.directory = rime_api.get_user_data_dir() .. '/yuekey-predict'
  local ctx = env.engine.context
  env.commit = ctx.commit_notifier:connect(function() env.pending = true end)
  env.update = ctx.update_notifier:connect(function(context)
    if not context.composition:empty() then return end
    local committed = env.pending
    env.pending = false
    if not committed or not context:get_option('prediction') or context:get_option('ascii_mode') then return end
    local record = context.commit_history:back()
    if not record or record.type == 'punct' or record.type == 'raw' or record.type == 'thru'
        or record.type == 'prediction' then return end
    local choices = lookup(env, record.text)
    if not choices or #choices == 0 then return end
    local segment = Segment(0, 0)
    segment.tags = Set({'prediction', 'placeholder'})
    segment.menu = Menu()
    segment.menu:add_translation(Translation(function()
      for _, text in ipairs(choices) do yield(Candidate('prediction', 0, 0, text, '')) end
    end))
    segment.menu:prepare(#choices)
    segment.status = 'kGuess'
    context.composition:push_back(segment)
  end)
end

function M.fini(env)
  env.commit:disconnect()
  env.update:disconnect()
end

function M.func(key, env)
  if key:release() or key:ctrl() or key:alt() or key:super() then return 2 end
  if key.keycode == 0xff08 or key.keycode == 0xff1b then
    env.pending = false
    local ctx = env.engine.context
    local segment = ctx.composition:back()
    if segment and segment:has_tag('prediction') then
      ctx:clear()
      return 1
    end
  end
  return 2
end

return M
