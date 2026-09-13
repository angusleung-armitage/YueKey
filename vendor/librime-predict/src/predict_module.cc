#include <rime/component.h>
#include <rime/registry.h>
#include <rime_api.h>

#include "predictor.h"
#include "predict_engine.h"
#include "predict_translator.h"

using namespace rime;

static void rime_quick_hk_predict_initialize() {
  Registry& r = Registry::instance();
  an<PredictEngineComponent> engine_factory = New<PredictEngineComponent>();
  r.Register("quick_hk_predictor", new PredictorComponent(engine_factory));
  r.Register("quick_hk_predict_translator",
             new PredictTranslatorComponent(engine_factory));
}

static void rime_quick_hk_predict_finalize() {}

RIME_REGISTER_MODULE(quick_hk_predict)
