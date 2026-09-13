#ifndef RIME_PREDICT_ENGINE_H_
#define RIME_PREDICT_ENGINE_H_

#include "predict_db.h"
#include <rime/component.h>
#include <rime/dict/db_pool.h>

namespace rime {

class Context;
class Engine;
struct Segment;
struct Ticket;
class Translation;

class PredictEngine : public Class<PredictEngine, const Ticket&> {
 public:
  PredictEngine(an<PredictDb> db, int max_iterations, int max_candidates,
                bool show_preedit);
  virtual ~PredictEngine();

  bool Predict(Context* ctx, const string& context_query);
  void Clear();
  void CreatePredictSegment(Context* ctx) const;
  an<Translation> Translate(const Segment& segment) const;

  int max_iterations() const { return max_iterations_; }
  int max_candidates() const { return max_candidates_; }
  string preedit(const string& text) const { return show_preedit_ ? text : string(); }
  const string& query() const { return query_; }
  int num_candidates() const { return candidates_ ? candidates_->size : 0; }
  string candidate(size_t i) const {
    return candidates_ ? db_->GetEntryText(candidates_->at[i]) : string();
  }

 private:
  an<PredictDb> db_;
  int max_iterations_;  // prediction times limit
  int max_candidates_;  // prediction candidate count limit
  bool show_preedit_;   // IBus needs panel composition to keep its menu visible
  string query_;        // cache last query
  const predict::Candidates* candidates_ = nullptr;  // cache last result
};

class PredictEngineComponent : public PredictEngine::Component {
 public:
  PredictEngineComponent();
  virtual ~PredictEngineComponent();

  PredictEngine* Create(const Ticket& ticket) override;

  an<PredictEngine> GetInstance(const Ticket& ticket);

 protected:
  map<Engine*, weak<PredictEngine>> predict_engine_by_input_context_;
  DbPool<PredictDb> db_pool_;
};

}  // namespace rime

#endif  // RIME_PREDICT_ENGINE_H_
