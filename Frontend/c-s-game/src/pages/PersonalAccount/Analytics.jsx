import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  fetchUserProfile,
  getToken,
  fetchTests,
  fetchUserAnswers,
  fetchMaterials,
} from '../../api/api';
import './Analytics.css';

const Analytics = () => {
  const [activeTab, setActiveTab] = useState('progress');
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState({
    materialsStudied: 0,
    totalMaterials: 0,
    testsCompleted: 0,
    totalTests: 0,
    averageScore: 0,
  });
  const [testResults, setTestResults] = useState([]);
  const navigate = useNavigate();

  const renderProgressBar = (percentage) => (
    <div className="progress-bar">
      <div className="progress-fill" style={{ width: `${percentage}%` }} />
    </div>
  );

  const getAverageScoreIn10Scale = (percent) => {
    if (percent === undefined || percent === null) return '—';
    const score = (percent / 10).toFixed(1);
    return score;
  };

  useEffect(() => {
    const loadAnalytics = async () => {
      if (!getToken()) {
        setLoading(false);
        return;
      }
      try {
        const materials = await fetchMaterials();
        const totalMaterials = materials.length;

        const tests = await fetchTests();
        const totalTests = tests.length;
        let completedTests = 0;
        let totalScoreSum = 0;
        let testsWithScore = 0;
        const results = [];

        for (const test of tests) {
          try {
            const answers = await fetchUserAnswers(test.id);
            if (answers && answers.length > 0) {
              completedTests++;
              const userScore = answers.reduce((sum, ans) => sum + (ans.score || 0), 0);
              const maxScore = test.max_score;
              if (maxScore) {
                const percentage = (userScore / maxScore) * 100;
                totalScoreSum += percentage;
                testsWithScore++;
                results.push({
                  id: test.id,
                  name: test.title,
                  score: Math.round(percentage),
                  date: answers[0]?.created_at
                    ? new Date(answers[0].created_at).toLocaleDateString('ru-RU')
                    : '—',
                });
              }
            }
          } catch (e) {}
        }
        const averageScore = testsWithScore > 0 ? Math.round(totalScoreSum / testsWithScore) : 0;

        setStats({
          materialsStudied: 0,
          totalMaterials,
          testsCompleted: completedTests,
          totalTests,
          averageScore,
        });
        setTestResults(results);
      } catch (error) {
        console.error('Ошибка загрузки аналитики:', error);
      } finally {
        setLoading(false);
      }
    };
    loadAnalytics();
  }, []);

  const handleBack = () => navigate('/personal-account');

  if (loading) return <div className="loading">Загрузка аналитики...</div>;

  return (
    <div className="analytics-page">
      <div className="analytics-container">
        <div className="analytics-header">
          <button className="back-button" onClick={handleBack}>
            Назад в личный кабинет
          </button>
          <h1>Аналитика обучения</h1>
          <p className="analytics-subtitle">Статистика вашего прогресса и результатов</p>
        </div>

        <div className="analytics-tabs">
          <button
            className={`tab-btn ${activeTab === 'progress' ? 'active' : ''}`}
            onClick={() => setActiveTab('progress')}
          >
            Прогресс
          </button>
          <button
            className={`tab-btn ${activeTab === 'tests' ? 'active' : ''}`}
            onClick={() => setActiveTab('tests')}
          >
            Тесты
          </button>
        </div>

        {activeTab === 'progress' && (
          <div className="analytics-content">
            <div className="stats-grid">
              <div className="stat-card">
                <div className="stat-header">
                  <h3>Материалы</h3>
                </div>
                <div className="stat-numbers">
                  <span className="stat-current">{stats.materialsStudied}</span>
                  <span className="stat-divider">/</span>
                  <span className="stat-total">{stats.totalMaterials}</span>
                </div>
                {renderProgressBar(
                  stats.totalMaterials ? (stats.materialsStudied / stats.totalMaterials) * 100 : 0
                )}
              </div>

              <div className="stat-card">
                <div className="stat-header">
                  <h3>Тесты</h3>
                </div>
                <div className="stat-numbers">
                  <span className="stat-current">{stats.testsCompleted}</span>
                  <span className="stat-divider">/</span>
                  <span className="stat-total">{stats.totalTests}</span>
                </div>
                {renderProgressBar(
                  stats.totalTests ? (stats.testsCompleted / stats.totalTests) * 100 : 0
                )}
              </div>

              <div className="stat-card">
                <div className="stat-header">
                  <h3>Средний балл (10‑балльная шкала)</h3>
                </div>
                <div className="stat-numbers">
                  <span className="stat-score">{getAverageScoreIn10Scale(stats.averageScore)}</span>
                </div>
                <div className="score-indicator">
                  <div className="score-bar">
                    <div className="score-fill" style={{ width: `${stats.averageScore}%` }} />
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {activeTab === 'tests' && (
          <div className="analytics-content">
            <div className="test-results-table">
              <h3>Результаты тестов</h3>
              <table>
                <thead>
                  <tr>
                    <th>Название теста</th>
                    <th>Результат</th>
                    <th>Дата прохождения</th>
                  </tr>
                </thead>
                <tbody>
                  {testResults.map((test) => (
                    <tr key={test.id}>
                      <td>{test.name}</td>
                      <td>
                        <div className="test-score-cell">
                          <span className="test-score">{test.score}%</span>
                          {renderProgressBar(test.score)}
                        </div>
                      </td>
                      <td>{test.date}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default Analytics;
