const API_BASE_URL = '/api/v1'; // соответствует префиксу из бэкенда

export const fetchMaterials = async () => {
  try {
    const response = await fetch(`${API_BASE_URL}/materials/`);
    if (!response.ok) {
      throw new Error(`Ошибка загрузки материалов: ${response.status}`);
    }
    return await response.json();
  } catch (error) {
    console.error('Ошибка запроса к бэкенду:', error);
    // Заглушка, чтобы фронтенд не падал (можно убрать, когда бэкенд будет готов)
    return [
      {
        id: 1,
        title: 'Введение в React.js (заглушка)',
        description: 'React — JavaScript-библиотека для создания интерфейсов.',
        created_at: '2024-01-15',
        tests: [],
      },
    ];
  }
};

export const fetchMaterialById = async (id) => {
  try {
    const response = await fetch(`${API_BASE_URL}/materials/${id}`);
    if (!response.ok) {
      throw new Error(`Ошибка загрузки материала: ${response.status}`);
    }
    return await response.json();
  } catch (error) {
    console.error('Ошибка запроса к бэкенду:', error);
    // Заглушка для одного материала
    return {
      id: parseInt(id),
      title: 'Материал не найден (заглушка)',
      content_text: 'Данные временно недоступны.',
      created_at: new Date().toISOString(),
      tests: [],
    };
  }
};
