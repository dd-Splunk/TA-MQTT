# TA-MQTT — Executive Summary (FR)

Date: 2026-03-14  
Objet: Synthèse décisionnelle de la revue statique du TA Custom

## Contexte

Une revue statique du TA-MQTT a été réalisée directement sur le code source pour identifier les limites potentielles de débit avant benchmark comparatif Splunk.

## Constat architecture (en l’état)

- 1 process modular input par stanza (`use_single_instance = False`)
- 1 client MQTT paho par stanza
- Réception des messages sur thread réseau paho
- Queue mémoire bornée (`maxsize=10_000`) entre callback MQTT et writer Splunk
- Écriture Splunk séquentielle événement par événement via `ew.write_event`

## Goulots majeurs identifiés

1. **Chemin d’écriture mono-writer et séquentiel (P0)**  
   Le traitement final est fait en boucle Python, un événement à la fois.

2. **Saturation queue + drops explicites (P0)**  
   Lorsque l’ingress dépasse l’egress, la queue se remplit puis les messages sont dropped.

3. **Coût CPU sur le chemin chaud (P1)**  
   Sérialisation JSON et construction d’objets par message dans la boucle writer.

4. **Paramètres de buffer figés (P1)**  
   `maxsize` et `drain_batch_size` hardcodés, donc tuning limité selon environnement.

## Impact business benchmark

Avec un critère de rupture à **0% de drop**, le mécanisme de saturation de queue devient le déclencheur principal du point de rupture observé côté TA.

## Recommandations prioritaires

- **R1 (P0)**: Ajouter un mode de sortie batch (ex: HEC batch), en conservant le mode actuel pour compatibilité.
- **R2 (P0)**: Réduire le coût CPU du writer (préparation/sérialisation déplacée ou allégée).
- **R3 (P1)**: Rendre configurables la taille de queue et le batch de drain.
- **R4 (P1)**: Évaluer parallélisation writer uniquement si compatibilité thread-safe confirmée.

## Décision attendue

Valider la trajectoire d’optimisation:

- **Option A**: Optimisation incrémentale sans changer de mode de sortie (R2 + R3)
- **Option B**: Ajout d’un mode batch en priorité (R1 + R2)

## Référence technique complète

Voir le rapport détaillé: `docs/static-analysis-2026-03-14.md`
